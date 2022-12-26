FROM debian:11.6

# Dependencies
RUN apt-get update && \
    apt-get install -y python3.9 python3-venv python3-setuptools python3-all \
        fakeroot debhelper dh-python

# Needed files
RUN mkdir /tmp/archy
COPY setup.py /tmp/archy
COPY archy /tmp/archy/archy
COPY requirements.txt /tmp/archy
COPY stdeb.cfg /tmp/archy
COPY test_data.sh /tmp/archy
RUN chmod u+x /tmp/archy/test_data.sh

# Installing archy
WORKDIR /tmp/archy
RUN python3.9 -m venv .venv && \
    . .venv/bin/activate && \
    pip install -r requirements.txt && \
    python3.9 setup.py --command-packages=stdeb.command bdist_deb
RUN export ARCHY_PKG=$(ls deb_dist | grep 'archy_[0-9\.\-]*_all.deb') && \
    dpkg -i deb_dist/$ARCHY_PKG || true && \
    apt-get -fy install

# Generating some test data.
WORKDIR /home
RUN /tmp/archy/test_data.sh

# Cleanup
RUN rm -rf /tmp/archy
