"""Parser tests using minimal Form 4 and Schedule 13D XML fixtures."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import edgar  # noqa: E402
import filters  # noqa: E402

FORM4_XML = """<?xml version="1.0"?>
<ownershipDocument>
  <documentType>4</documentType>
  <issuer>
    <issuerCik>0000123456</issuerCik>
    <issuerName>Acme Bio Inc.</issuerName>
    <issuerTradingSymbol>ACME</issuerTradingSymbol>
  </issuer>
  <reportingOwner>
    <reportingOwnerId>
      <rptOwnerCik>0000999888</rptOwnerCik>
      <rptOwnerName>Doe Jane</rptOwnerName>
    </reportingOwnerId>
    <reportingOwnerRelationship>
      <isDirector>0</isDirector>
      <isOfficer>1</isOfficer>
      <isTenPercentOwner>0</isTenPercentOwner>
      <officerTitle>Chief Executive Officer</officerTitle>
    </reportingOwnerRelationship>
  </reportingOwner>
  <nonDerivativeTable>
    <nonDerivativeTransaction>
      <securityTitle><value>Common Stock</value></securityTitle>
      <transactionDate><value>2026-06-25</value></transactionDate>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionAmounts>
        <transactionShares><value>10000</value></transactionShares>
        <transactionPricePerShare><value>12.50</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
    <nonDerivativeTransaction>
      <transactionCoding><transactionCode>P</transactionCode></transactionCoding>
      <transactionDate><value>2026-06-26</value></transactionDate>
      <transactionAmounts>
        <transactionShares><value>5000</value></transactionShares>
        <transactionPricePerShare><value>13.00</value></transactionPricePerShare>
      </transactionAmounts>
    </nonDerivativeTransaction>
  </nonDerivativeTable>
</ownershipDocument>"""

SALE_XML = FORM4_XML.replace("<transactionCode>P</transactionCode>",
                             "<transactionCode>S</transactionCode>")

SC13D_XML = """<?xml version="1.0" encoding="UTF-8"?>
<edgarSubmission xmlns="http://www.sec.gov/edgar/schedule13D"
                 xmlns:com="http://www.sec.gov/edgar/common">
  <headerData>
    <submissionType>SCHEDULE 13D</submissionType>
  </headerData>
  <formData>
    <coverPageHeader>
      <issuerInfo>
        <issuerCIK>0000123456</issuerCIK>
        <issuerName>Acme Bio Inc.</issuerName>
      </issuerInfo>
    </coverPageHeader>
    <coverPageHeaderReportingPersonDetails>
      <percentOfClass>7.5</percentOfClass>
    </coverPageHeaderReportingPersonDetails>
  </formData>
</edgarSubmission>"""


def _rec(acc="0000111111-26-000001"):
    return {"accession": acc, "form_internal": "4", "ciks": ["123456"],
            "filed_date": "2026-06-26", "doc": "form4.xml",
            "source": {"display_names": ["BVF Partners L P (CIK 0000999888)",
                                          "Acme Bio Inc. (CIK 0000123456)"]}}


def test_form4_aggregates_purchases():
    f = edgar.parse_form4(FORM4_XML, _rec())
    assert f is not None
    assert f.transaction_code == "P"
    assert f.shares == 15000
    # weighted value = 10000*12.5 + 5000*13 = 125000 + 65000 = 190000
    assert f.trade_value == 190000
    assert abs(f.trade_price - 190000 / 15000) < 1e-3  # trade_price rounded to 4dp
    assert f.ticker == "ACME"
    assert f.insider_title == "Chief Executive Officer"
    assert f.trade_date == "2026-06-26"


def test_form4_sale_is_dropped():
    f = edgar.parse_form4(SALE_XML, _rec())
    assert f is None  # no P-code purchases -> not scorable


def test_prefilter_rejects_small_trade():
    f = edgar.parse_form4(FORM4_XML, _rec())
    f.trade_value = 50_000
    reason = filters.prefilter(f)
    assert reason and "trade value" in reason


def test_prefilter_rejects_10b5_1():
    f = edgar.parse_form4(FORM4_XML, _rec())
    f.is_10b5_1 = True
    assert filters.prefilter(f) == "10b5-1 pre-scheduled plan"


def test_schedule13d_parse():
    rec = _rec()
    rec["form_internal"] = "13D"
    f = edgar.parse_schedule13(SC13D_XML, rec)
    assert f is not None
    assert f.filing_type == "13D"
    assert f.percent_of_class == 7.5
    assert f.is_new_position is True
    assert f.issuer_name == "Acme Bio Inc."
