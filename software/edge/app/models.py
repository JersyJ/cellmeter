from typing import Annotated, Any

from pydantic import AliasPath, BaseModel, ConfigDict, Field, model_validator


class SessionRequest(BaseModel):
    """Model for session start request payload."""

    auto_benchmarks: bool = Field(
        False,
        description="Flag to enable or disable automatic benchmarks during the session.",
    )


class BaseSessionResponse(BaseModel):
    """Base model for session responses."""

    session_id: Annotated[str, Field(description="Unique identifier for the session.")] | None = (
        None
    )

    iccid: (
        Annotated[str, Field(description="ICCID of the SIM card used in the session.")] | None
    ) = None
    benchmark_in_progress: (
        Annotated[bool, Field(description="Indicates if benchmarks are running for the session.")]
        | None
    ) = None
    auto_benchmarks: (
        Annotated[
            bool,
            Field(description="Indicates if automatic benchmarks are enabled for the session."),
        ]
        | None
    ) = None


class SessionResponse(BaseSessionResponse):
    """Defines the structured JSON response for the session endpoint."""

    message: str = Field(
        ...,
        description="Human-readable message describing the info about the session.",
    )


class HighFrequencyStateTeltonikaResponse(BaseModel):
    """
    A Pydantic model that uses AliasPath for declarative parsing of the
    nested Teltonika API response.
    """

    model_config = ConfigDict(validate_by_alias=True, validate_by_name=True)

    # Radio Signal Metrics
    rsrp: int | None = Field(None, validation_alias=AliasPath("data", 0, "rsrp"))
    rsrq: int | None = Field(None, validation_alias=AliasPath("data", 0, "rsrq"))
    sinr: int | None = Field(None, validation_alias=AliasPath("data", 0, "sinr"))
    # Network Identifiers
    cell_id: int | None = Field(None, validation_alias=AliasPath("data", 0, "cellid"))
    tracking_area_code: int | None = Field(None, validation_alias=AliasPath("data", 0, "tac"))
    network_type: str | None = Field(None, validation_alias=AliasPath("data", 0, "ntype"))
    frequency_band: str | None = Field(
        None, validation_alias=AliasPath("data", 0, "cell_info", 0, "bandwidth")
    )
    frequency_channel: int | None = Field(None)
    physical_cell_id: int | None = Field(
        None, validation_alias=AliasPath("data", 0, "cell_info", 0, "pcid")
    )
    operator: str | None = Field(None, validation_alias=AliasPath("data", 0, "operator"))
    # Device Status
    modem_temperature: int | None = Field(
        None, validation_alias=AliasPath("data", 0, "temperature")
    )

    @model_validator(mode="before")
    @classmethod
    def choose_frequency_channel(cls, data: Any) -> Any:
        def is_valid(value):
            if value is None:
                return False
            return not (
                isinstance(value, str) and value.strip().upper().replace("\\", "") in {"N/A", "NA"}
            )

        try:
            cell_info = data["data"][0]["cell_info"][0]
        except (KeyError, IndexError, TypeError):
            return data

        # Priority list
        priorities = [
            "nr-arfcn",  # 5G
            "earfcn",  # 4G/LTE
            "uarfcn",  # 3G/UMTS
            "arfcn",  # 2G/GMS
        ]

        for key in priorities:
            val = cell_info.get(key)
            if is_valid(val):
                try:
                    data["frequency_channel"] = int(val)
                    break
                except (ValueError, TypeError):
                    continue
        else:
            data["frequency_channel"] = None

        return data

    @model_validator(mode="before")
    @classmethod
    def replace_na_with_none(cls, data: Any) -> Any:
        """Fast normalization: turn 'N/A' or 'N\\/A' anywhere into None."""
        if not isinstance(data, (dict, list)):
            return data

        stack = [data]
        while stack:
            item = stack.pop()
            if isinstance(item, dict):
                for k, v in item.items():
                    if isinstance(v, str):
                        vv = v.strip().upper().replace("\\", "")
                        if vv in {"N/A", "NA", ""}:
                            item[k] = None
                    elif isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(item, list):
                for i, v in enumerate(item):
                    if isinstance(v, str):
                        vv = v.strip().upper().replace("\\", "")
                        if vv in {"N/A", "NA", ""}:
                            item[i] = None
                    elif isinstance(v, (dict, list)):
                        stack.append(v)
        return data


class PingResult(BaseModel):
    rtt_avg_ms: float | None = None
    packet_loss_pct: float | None = None


class Iperf3Result(BaseModel):
    upload_mbps: float | None = None
    download_mbps: float | None = None
    jitter_ms: float | None = None


class SpeedtestResult(BaseModel):
    upload_mbps: float | None = None
    download_mbps: float | None = None


class ManualBenchmarkResponse(BaseModel):
    """Response model for the manual benchmark trigger endpoint."""

    message: str = Field(..., description="A confirmation message.")
