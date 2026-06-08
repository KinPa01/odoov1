FROM odoo:19.0

USER root

# Install Thai fonts so wkhtmltopdf can render Thai text correctly in PDF reports
# Without these, Thai characters appear as black squares (tofu)
RUN apt-get update -qq \
    && apt-get install -y -qq --no-install-recommends \
        fonts-thai-tlwg \
        fonts-arundina \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

USER odoo
