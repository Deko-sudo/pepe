from __future__ import annotations


class ProviderError(Exception):
    code = "provider_error"
    retryable = False
    public_message = "Market data provider error."

    def __init__(self, *, retry_after_seconds: int | None = None) -> None:
        if retry_after_seconds is not None and not 1 <= retry_after_seconds <= 3_600:
            raise ValueError("retry_after_seconds must be between 1 and 3600")
        self.retry_after_seconds = retry_after_seconds
        super().__init__(self.public_message)


class InstrumentNotMapped(ProviderError):
    code = "instrument_not_mapped"
    public_message = "Instrument is not mapped to a market data provider."


class InstrumentUnsupported(ProviderError):
    code = "instrument_unsupported"
    public_message = "Instrument is not supported by the market data provider."


class ProviderUnavailable(ProviderError):
    code = "provider_unavailable"
    retryable = True
    public_message = "Market data provider is temporarily unavailable."


class ProviderAuthenticationFailure(ProviderError):
    code = "provider_authentication_failure"
    public_message = "Market data provider authentication failed."


class ProviderRateLimited(ProviderError):
    code = "provider_rate_limited"
    retryable = True
    public_message = "Market data provider rate limit has been reached."


class InvalidProviderResponse(ProviderError):
    code = "invalid_provider_response"
    public_message = "Market data provider returned an invalid response."


class StaleProviderMetadata(ProviderError):
    code = "stale_provider_metadata"
    public_message = "Market data provider metadata is stale."


class TemporaryTransportFailure(ProviderError):
    code = "temporary_transport_failure"
    retryable = True
    public_message = "Market data transport is temporarily unavailable."


class PermanentConfigurationFailure(ProviderError):
    code = "permanent_configuration_failure"
    public_message = "Market data provider configuration is invalid."
