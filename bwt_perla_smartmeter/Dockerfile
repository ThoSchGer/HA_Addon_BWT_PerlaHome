ARG BUILD_FROM
FROM ${BUILD_FROM}

# Systempakete (apk) – keine pip installs ins System-Python
RUN apk add --no-cache \
    python3 py3-pip bash jq \
    tesseract-ocr tesseract-ocr-data-eng \
    py3-pillow py3-paho-mqtt \
    py3-twisted py3-cryptography py3-service_identity

# Virtuelle Umgebung anlegen und dort pip verwenden
RUN python3 -m venv /opt/venv \
 && /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
 && /opt/venv/bin/pip install --no-cache-dir \
      pytesseract==0.3.10 \
      vncdotool==1.2.0

WORKDIR /opt/app
COPY app /opt/app/app
COPY run.sh /run.sh
RUN chmod +x /run.sh

CMD ["/run.sh"]
