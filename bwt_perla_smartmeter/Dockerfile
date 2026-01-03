ARG BUILD_FROM
FROM ${BUILD_FROM}

# System: Python + Tools + Tesseract
# Python deps: Twisted/Cryptography als apk, um Wheel-Builds auf Alpine zu vermeiden
RUN apk add --no-cache \
    python3 py3-pip bash jq \
    tesseract-ocr tesseract-ocr-data-eng \
    py3-pillow py3-paho-mqtt py3-pytesseract \
    py3-twisted py3-cryptography py3-service_identity \
 && python3 -m pip install --no-cache-dir --upgrade pip

# vncdotool via pip (nutzt dann die bereits installierten Twisted deps)
RUN python3 -m pip install --no-cache-dir vncdotool==1.2.0

WORKDIR /opt/app
COPY app /opt/app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
