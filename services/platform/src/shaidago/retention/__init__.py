"""Retention, deletion, and operational privacy: bounded purges and crypto-shredding.

These are run by an operator with the migration owner role (``make retention-purge``), never by an
API process, and every one is safe to repeat. What they enforce is technical; the retention
periods are prototype defaults and the legal basis for any real period is not decided here.
"""
