FROM python:3.12-slim

RUN pip install --no-cache-dir pytest==8.3.5 coverage==7.6.12 \
    && useradd --create-home --uid 10001 fencepost

# The source tree is deliberately mounted read-only.  Python's normal
# __pycache__ location would therefore make compileall and imports fail before
# pytest runs; place bytecode on the writable /tmp tmpfs instead.
ENV PYTHONPYCACHEPREFIX=/tmp/pycache \
    PYTHONPATH=/workspace

COPY docker/runner.sh /usr/local/bin/fencepost-run
COPY docker/batch_driver.py /opt/fencepost/batch_driver.py
COPY docker/coveragerc /opt/fencepost/coveragerc
RUN chmod 0555 /usr/local/bin/fencepost-run

USER fencepost
WORKDIR /workspace
ENTRYPOINT ["fencepost-run"]
