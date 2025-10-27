from pydantic import AliasChoices, AliasPath, BaseModel, Field


class BaseSessionResponse(BaseModel):
    """Base model for session responses."""

    session_id: str | None = Field(
        None,
        description="Unique identifier for the session.",
    )
    iccid: str | None = Field(
        None,
        description="ICCID of the SIM card used in the session.",
    )



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
    physical_cell_id: str | None = Field(None, validation_alias=AliasPath("data", 0, "cell_info", 0, "pcid"))
    operator: str | None = Field(None, validation_alias=AliasPath("data", 0, "operator"))
    # Device Status
    modem_temperature: float | None = Field(None, validation_alias=AliasPath("data", 0, "temperature"))
