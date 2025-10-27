from typing import Annotated

from pydantic import AliasChoices, AliasPath, BaseModel, Field


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

    # Radio Signal Metrics
    rsrp: str | None = Field(None, validation_alias=AliasPath("data", 0, "rsrp"))
    rsrq: str | None = Field(None, validation_alias=AliasPath("data", 0, "rsrq"))
    sinr: str | None = Field(None, validation_alias=AliasPath("data", 0, "sinr"))
    # Network Identifiers
    cell_id: str | None = Field(None, validation_alias=AliasPath("data", 0, "cellid"))
    tracking_area_code: str | None = Field(None, validation_alias=AliasPath("data", 0, "tac"))
    network_type: str | None = Field(None, validation_alias=AliasPath("data", 0, "ntype"))
    frequency_band: str | None = Field(
        None, validation_alias=AliasPath("data", 0, "cell_info", 0, "bandwidth")
    )
    frequency_channel: str | None = Field(
        None,
        validation_alias=AliasChoices(
            AliasPath("data", 0, "cell_info", 0, "nr-arfcn"),  # Priority 1: 5G
            AliasPath("data", 0, "cell_info", 0, "earfcn"),  # Priority 2: 4G/LTE
            AliasPath("data", 0, "cell_info", 0, "uarfcn"),  # Priority 3: 3G/UMTS
            AliasPath("data", 0, "cell_info", 0, "arfcn"),  # Priority 4: 2G/GSM
        ),
    )
    physical_cell_id: str | None = Field(
        None, validation_alias=AliasPath("data", 0, "cell_info", 0, "pcid")
    )
    operator: str | None = Field(None, validation_alias=AliasPath("data", 0, "operator"))
    # Device Status
    modem_temperature: float | None = Field(
        None, validation_alias=AliasPath("data", 0, "temperature")
    )


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
