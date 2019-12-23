import pytest
import json

from indy.ledger import build_txn_author_agreement_request

from plenum.common.constants import REPLY, OP_FIELD_NAME, DATA, TXN_AUTHOR_AGREEMENT_RETIREMENT_TS, \
    TXN_AUTHOR_AGREEMENT_RATIFICATION_TS, TXN_AUTHOR_AGREEMENT_VERSION, TXN_AUTHOR_AGREEMENT_TEXT
from plenum.common.exceptions import RequestNackedException, RequestRejectedException
from plenum.common.types import OPERATION
from plenum.common.util import randomString, get_utc_epoch

from plenum.test.helper import sdk_get_and_check_replies
from plenum.test.pool_transactions.helper import sdk_sign_and_send_prepared_request
from .helper import sdk_send_txn_author_agreement, sdk_get_txn_author_agreement


def test_send_valid_txn_author_agreement_before_aml_fails(set_txn_author_agreement):
    with pytest.raises(
            RequestRejectedException,
            match='TAA txn is forbidden until TAA AML is set. Send TAA AML first'
    ):
        set_txn_author_agreement()


def test_send_valid_txn_author_agreement_succeeds(
        set_txn_author_agreement_aml, set_txn_author_agreement, get_txn_author_agreement
):
    # TODO it might make sense to check that update_txn_author_agreement
    # was called with expected set of arguments
    assert set_txn_author_agreement() == get_txn_author_agreement()


def test_send_empty_txn_author_agreement_succeeds(
    set_txn_author_agreement_aml, set_txn_author_agreement, get_txn_author_agreement
):
    assert set_txn_author_agreement(text="") == get_txn_author_agreement()


def test_send_invalid_txn_author_agreement_fails(
        looper, set_txn_author_agreement_aml, txnPoolNodeSet, sdk_pool_handle, sdk_wallet_trustee, random_taa
):
    req = looper.loop.run_until_complete(
        build_txn_author_agreement_request(sdk_wallet_trustee[1], *random_taa)
    )
    req = json.loads(req)
    req[OPERATION]['text'] = 42
    rep = sdk_sign_and_send_prepared_request(looper, sdk_wallet_trustee, sdk_pool_handle, json.dumps(req))
    with pytest.raises(RequestNackedException):
        sdk_get_and_check_replies(looper, [rep])


def test_create_txn_author_agreement_succeeds(looper, set_txn_author_agreement_aml, sdk_pool_handle, sdk_wallet_trustee):
    # Write random TAA
    version, text, ratified = randomString(16), randomString(1024), get_utc_epoch() - 600
    sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                  version=version,
                                  text=text,
                                  ratified=ratified)

    # Make sure TAA successfully written as latest TAA
    rep = sdk_get_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee)[1]
    assert rep[OP_FIELD_NAME] == REPLY
    taa = rep['result'][DATA]
    assert taa[TXN_AUTHOR_AGREEMENT_VERSION] == version
    assert taa[TXN_AUTHOR_AGREEMENT_TEXT] == text
    assert taa[TXN_AUTHOR_AGREEMENT_RATIFICATION_TS] == ratified
    assert TXN_AUTHOR_AGREEMENT_RETIREMENT_TS not in taa

    # Make sure TAA also available using version
    rep = sdk_get_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee, version=version)[1]
    assert rep[OP_FIELD_NAME] == REPLY
    assert rep['result'][DATA] == taa


def test_create_txn_author_agreement_without_text_fails(looper, set_txn_author_agreement_aml,
                                                        sdk_pool_handle, sdk_wallet_trustee):
    with pytest.raises(RequestRejectedException):
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                      version=randomString(16),
                                      ratified=get_utc_epoch() - 600)


def test_create_txn_author_agreement_without_ratified_fails(looper, set_txn_author_agreement_aml,
                                                            sdk_pool_handle, sdk_wallet_trustee):
    with pytest.raises(RequestRejectedException):
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                      version=randomString(16),
                                      text=randomString(1024))


def test_create_txn_author_agreement_with_ratified_from_future_fails(looper, set_txn_author_agreement_aml,
                                                                     sdk_pool_handle, sdk_wallet_trustee):
    with pytest.raises(RequestRejectedException):
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                      version=randomString(16),
                                      text=randomString(1024),
                                      ratified=get_utc_epoch() + 600)


@pytest.mark.parametrize('retired_offset', [-600, 600])
def test_create_txn_author_agreement_with_retired_date_fails(looper, set_txn_author_agreement_aml,
                                                             sdk_pool_handle, sdk_wallet_trustee,
                                                             retired_offset):
    with pytest.raises(RequestRejectedException):
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                      version=randomString(16),
                                      text=randomString(1024),
                                      ratified=get_utc_epoch() - 600,
                                      retired=get_utc_epoch() + retired_offset)


def test_txn_author_agreement_update_text_fails(looper, set_txn_author_agreement_aml,
                                                sdk_pool_handle, sdk_wallet_trustee):
    # Write random TAA
    version, text, ratified = randomString(16), randomString(1024), get_utc_epoch() - 600
    sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                  version=version,
                                  text=text,
                                  ratified=ratified)

    # Try to update text
    with pytest.raises(RequestRejectedException):
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                      version=version,
                                      text=randomString(256),
                                      ratified=ratified)


@pytest.mark.parametrize('ratified_offset', [-600, 600])
def test_txn_author_agreement_update_ratification_fails(looper, set_txn_author_agreement_aml,
                                                        sdk_pool_handle, sdk_wallet_trustee, ratified_offset):
    # Write random TAA
    version, text, ratified = randomString(16), randomString(1024), get_utc_epoch() - 600
    sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                  version=version,
                                  text=text,
                                  ratified=ratified)

    # Try to update ratification timestamp
    with pytest.raises(RequestRejectedException):
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_trustee,
                                      version=version,
                                      text=text,
                                      ratified=ratified + ratified_offset)


def test_send_valid_txn_author_agreement_without_enough_privileges_fails(
        looper, set_txn_author_agreement_aml, txnPoolNodeSet,
        sdk_pool_handle, sdk_wallet_steward, random_taa
):
    with pytest.raises(RequestRejectedException):
        text, version = random_taa
        sdk_send_txn_author_agreement(looper, sdk_pool_handle, sdk_wallet_steward, version, text)
