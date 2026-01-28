FROM odoo:19

USER root
RUN pip3 install openpyxl ofxparse qifparse --break-system-packages
USER odoo
