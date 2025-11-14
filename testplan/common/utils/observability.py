"""
Observability tests
"""

import os


class _NoopSpan:
    """
    Span that does nothing when telemetry is not needed
    """

    def __enter__(self):
        print("entering span")
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class _Tracing:
    """
    Global tracing object to handle different kinds of tracing
    """

    def __init__(self):
        self._span_ctx = _NoopSpan()
        self.span = self._span_ctx
        self._initialized = True

    def _empty_span(self, *args, **kwargs):
        print(
            "Tracing span",
            self._span_ctx,
            "called with args:",
            args,
            "and kwargs:",
            kwargs,
        )
        return self._span_ctx

    def setup_otel_grpc(self):
        """Setup OpenTelemetry tracing with gRPC exporter"""
        if any(k.startswith("OTEL_") for k in os.environ):
            try:
                from opentelemetry import trace
                from opentelemetry.sdk.resources import Resource
                from opentelemetry.sdk.trace import TracerProvider
                from opentelemetry.sdk.trace.export import BatchSpanProcessor
                from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                    OTLPSpanExporter,
                )

                # Get resource attributes from environment variables
                prefix = "OTEL_RESOURCE_ATTRIBUTES_"
                attrs = {
                    k[len(prefix) :]: v
                    for k, v in os.environ.items()
                    if k.startswith(prefix) and k[len(prefix) :]
                }

                # Also support OTEL_RESOURCE_ATTRIBUTES="k1=v1,k2=v2"
                raw = os.getenv("OTEL_RESOURCE_ATTRIBUTES")
                if raw:
                    for part in raw.split(","):
                        if "=" in part:
                            k, v = part.split("=", 1)
                            k = k.strip()
                            v = v.strip()
                            if k and v and k not in attrs:
                                attrs[k] = v

                resource = Resource.create(attrs)

                provider = TracerProvider(resource=resource)
                processor = BatchSpanProcessor(OTLPSpanExporter())
                provider.add_span_processor(processor)
                trace.set_tracer_provider(provider)

                self._tracer = trace.get_tracer("testplan_oss_tests")

                def _span(*args, **kwargs):
                    print(
                        "Tracing span (gRPC) called with args:",
                        args,
                        "and kwargs:",
                        kwargs,
                    )
                    return self._tracer.start_as_current_span(
                        kwargs.get("name", "<step>"),
                        attributes=kwargs,
                    )

                self.span = _span

            except Exception as e:
                print("Failed to setup OpenTelemetry gRPC:", e)


tracing = _Tracing()
