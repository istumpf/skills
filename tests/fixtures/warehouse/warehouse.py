"""Existing warehouse integration; preserve these public values and behavior."""
SCHEMA_VERSION = 1


def stock_key(site, sku):
    return site.strip().upper() + ":" + sku.strip().upper()
