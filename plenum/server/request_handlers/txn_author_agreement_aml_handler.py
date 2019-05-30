from functools import lru_cache
from typing import Optional

from common.serializers.serialization import pool_state_serializer, config_state_serializer
from plenum.common.constants import POOL_LEDGER_ID, NODE, DATA, BLS_KEY, \
    BLS_KEY_PROOF, TARGET_NYM, DOMAIN_LEDGER_ID, NODE_IP, \
    NODE_PORT, CLIENT_IP, CLIENT_PORT, ALIAS, TXN_AUTHOR_AGREEMENT, CONFIG_LEDGER_ID, TXN_AUTHOR_AGREEMENT_AML, AML, \
    AML_VERSION
from plenum.common.exceptions import InvalidClientRequest, UnauthorizedClientRequest
from plenum.common.request import Request
from plenum.common.txn_util import get_payload_data, get_from
from plenum.common.types import f
from plenum.server.database_manager import DatabaseManager
from plenum.server.request_handlers.handler_interfaces.write_request_handler import WriteRequestHandler
from plenum.server.request_handlers.static_taa_helper import StaticTAAHelper
from plenum.server.request_handlers.utils import is_steward


class TxnAuthorAgreementAmlHandler(WriteRequestHandler):
    state_serializer = pool_state_serializer

    def __init__(self, database_manager: DatabaseManager, bls_crypto_verifier):
        super().__init__(database_manager, TXN_AUTHOR_AGREEMENT_AML, CONFIG_LEDGER_ID)
        self.bls_crypto_verifier = bls_crypto_verifier

    def static_validation(self, request: Request):
        operation, identifier, req_id = request.operation, request.identifier, request.reqId
        if len(operation[AML]) == 0:
            raise InvalidClientRequest(identifier, req_id,
                                       "TXN_AUTHOR_AGREEMENT_AML request "
                                       "must contain at least one acceptance mechanism")

    def dynamic_validation(self, request: Request):
        self._validate_request_type(request)
        StaticTAAHelper.authorize(self.database_manager, request)
        operation, identifier, req_id = request.operation, request.identifier, request.reqId
        version = operation.get(AML_VERSION)
        if StaticTAAHelper.get_taa_aml_data(self.state, version, isCommitted=False) is not None:
            raise InvalidClientRequest(identifier, req_id,
                                       "Version of TAA AML must be unique and it cannot be modified")

    def update_state(self, txn, prev_result, is_committed=False):
        self._validate_txn_type(txn)
        payload = get_payload_data(txn)
        version = payload[AML_VERSION]
        payload = config_state_serializer.serialize(payload)
        self.state.set(StaticTAAHelper.state_path_taa_aml_latest(), payload)
        self.state.set(StaticTAAHelper.state_path_taa_aml_version(version), payload)
