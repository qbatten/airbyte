#
# Copyright (c) 2023 Airbyte, Inc., all rights reserved.
#

from dataclasses import InitVar, dataclass
from typing import Any, List, Mapping, Optional

import pendulum
from airbyte_cdk.sources.declarative.interpolation.interpolated_boolean import InterpolatedBoolean
from airbyte_cdk.sources.declarative.types import Config, StreamSlice, StreamState


@dataclass
class RecordFilter:
    """
    Filter applied on a list of Records

    config (Config): The user-provided configuration as specified by the source's spec
    condition (str): The string representing the predicate to filter a record. Records will be removed if evaluated to False
    """

    parameters: InitVar[Mapping[str, Any]]
    config: Config
    condition: str = ""

    def __post_init__(self, parameters: Mapping[str, Any]) -> None:
        self._filter_interpolator = InterpolatedBoolean(condition=self.condition, parameters=parameters)

    def filter_records(
        self,
        records: List[Mapping[str, Any]],
        stream_state: StreamState,
        stream_slice: Optional[StreamSlice] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> List[Mapping[str, Any]]:
        kwargs = {"stream_state": stream_state, "stream_slice": stream_slice, "next_page_token": next_page_token}
        return [record for record in records if self._filter_interpolator.eval(self.config, record=record, **kwargs)]


class ClientSideIncrementalRecordFilterDecorator:
    # TODO: refactor to generalize : current implementation is based on MailChimp
    """
    Filter applied on a list of Records to exclude ones that are older than stream_state/start_date
    config (Config): The user-provided configuration as specified by the source's spec
    """

    def __init__(self, cursor_field: str, record_filter: Optional[RecordFilter], config: Config, start_date_from_config: str):
        self._cursor_field = cursor_field
        self._delegate = record_filter
        self._config = config
        self._start_date_from_config = start_date_from_config

    def filter_records(
        self,
        records: List[Mapping[str, Any]],
        stream_state: StreamState,
        stream_slice: Optional[StreamSlice] = None,
        next_page_token: Optional[Mapping[str, Any]] = None,
    ) -> List[Mapping[str, Any]]:
        state_value = self.get_state_value(stream_state, stream_slice)
        filter_date = self.get_filter_date(state_value)
        records = [record for record in records if record[self._cursor_field] > filter_date]
        if self._delegate:
            return self._delegate.filter_records(
                records=records, stream_state=stream_state, stream_slice=stream_slice, next_page_token=next_page_token
            )
        return records

    def get_state_value(self, stream_state: StreamState, stream_slice: StreamSlice) -> Optional[str]:
        state_value = None
        if stream_state.get("states"):
            state = [x for x in stream_state.get("states", []) if x["partition"]["id"] == stream_slice.partition["id"]]
            if state:
                state_value = state[0]["cursor"][self._cursor_field]
        else:
            state_value = stream_state.get(self._cursor_field)
        return state_value

    def get_filter_date(self, state_value: str) -> str:
        start_date_parsed = pendulum.parse(self._start_date_from_config) if self._start_date_from_config else None
        state_date_parsed = pendulum.parse(state_value) if state_value else None

        # Return the max of the two dates if both are present. Otherwise return whichever is present, or None.
        if start_date_parsed or state_date_parsed:
            return max(filter(None, [start_date_parsed, state_date_parsed]), default=None)
