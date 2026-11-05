FROM python:3.12-slim
WORKDIR /app
COPY --chown=65534:65534 engineering/ engineering/
COPY --chown=65534:65534 fixtures/ fixtures/
RUN mkdir artifacts && chown -R 65534:65534 artifacts
USER 65534:65534
ENTRYPOINT ["python", "-m", "engineering.cli"]
CMD ["demo"]
