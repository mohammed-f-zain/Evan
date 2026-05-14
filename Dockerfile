FROM odoo:18.0
USER root
RUN pip3 install --no-cache-dir --break-system-packages \
    openpyxl \
    ofxparse \
    qifparse
USER odoo
