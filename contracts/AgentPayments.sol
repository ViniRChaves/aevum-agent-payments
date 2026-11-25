// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/// @title AgentPayments — pagamentos programáveis para agentes (QDay testnet)
/// @notice Cofre + mandatos verificáveis + session keys com escopo restrito.
///         O contrato é a ÚLTIMA linha de defesa: nenhum pagamento sai do
///         cofre sem (1) mandato ativo assinado pelo dono, (2) teto
///         respeitado, (3) session key válida dentro do seu escopo.
///         Tudo é testnet (chain 44005) e tokens de teste (tUSD8).
interface IERC20 {
    function transfer(address to, uint256 amount) external returns (bool);
    function transferFrom(address from, address to, uint256 amount) external returns (bool);
    function balanceOf(address account) external view returns (uint256);
}

contract AgentPayments {
    // ------------------------------------------------------------------ tipos
    struct Mandate {
        address beneficiary;
        uint256 cap;      // teto total do mandato (tUSD8, 6 decimais)
        uint256 spent;    // já pago dentro deste mandato
        uint256 expiry;   // timestamp UNIX — depois disso, nada sai
        bool active;
    }

    struct SessionKey {
        bytes32 mandateId; // mandato ao qual esta chave está vinculada
        uint256 maxValue;  // teto por pagamento desta chave
        uint256 expiry;    // validade da chave
        bool active;
    }

    // ------------------------------------------------------------------ estado
    IERC20 public immutable token; // tUSD8 oficial: 0x456569838f1d43009A91ebA4263147Afd7233483
    address public owner;
    uint256 public nonce; // anti-replay dos mandatos assinados (EIP-712)

    mapping(bytes32 => Mandate) public mandates;
    mapping(address => SessionKey) public sessionKeys;

    bytes32 public immutable domainSeparator;
    bytes32 public constant MANDATE_TYPEHASH =
        keccak256("Mandate(address beneficiary,uint256 cap,uint256 expiry,uint256 nonce)");

    // ------------------------------------------------------------------ eventos
    event MandateCreated(bytes32 indexed mandateId, address indexed beneficiary, uint256 cap, uint256 expiry);
    event MandateRevoked(bytes32 indexed mandateId);
    event SessionKeyRegistered(address indexed key, bytes32 indexed mandateId, uint256 maxValue, uint256 expiry);
    event SessionKeyRevoked(address indexed key);
    event Deposited(address indexed from, uint256 amount);
    event Withdrawn(address indexed to, uint256 amount);
    event PaymentExecuted(bytes32 indexed mandateId, address indexed caller, address indexed beneficiary, uint256 amount);

    // ------------------------------------------------------------------ erros
    error NotOwner();
    error MandateNotFound();
    error MandateInactive();
    error MandateExpired();
    error BadSignature();
    error BadExpiry();
    error ZeroAmount();
    error OverMandateCap();
    error SessionKeyNotFound();
    error SessionKeyInactive();
    error SessionKeyExpired();
    error SessionKeyWrongMandate();
    error OverSessionKeyMax();
    error InsufficientVaultBalance();
    error TransferFailed();

    modifier onlyOwner() {
        if (msg.sender != owner) revert NotOwner();
        _;
    }

    constructor(address _token) {
        token = IERC20(_token);
        owner = msg.sender;
        domainSeparator = keccak256(
            abi.encode(
                keccak256("EIP712Domain(string name,string version,uint256 chainId,address verifyingContract)"),
                keccak256(bytes("AgentPayments")),
                keccak256(bytes("1")),
                block.chainid,
                address(this)
            )
        );
    }

    // ------------------------------------------------------- mandato (EIP-712)
    /// @notice Cria um mandato a partir da intenção ASSINADA pelo dono
    ///         (beneficiário, teto e validade). Qualquer um pode submeter
    ///         a transação; só a assinatura do dono a torna válida.
    function createMandate(
        address beneficiary,
        uint256 cap,
        uint256 expiry,
        bytes calldata signature
    ) external returns (bytes32 mandateId) {
        if (beneficiary == address(0)) revert MandateNotFound();
        if (cap == 0) revert ZeroAmount();
        if (expiry <= block.timestamp) revert BadExpiry();

        bytes32 structHash = keccak256(
            abi.encode(MANDATE_TYPEHASH, beneficiary, cap, expiry, nonce)
        );
        bytes32 digest = keccak256(abi.encodePacked("\x19\x01", domainSeparator, structHash));
        address signer = _recover(digest, signature);
        if (signer != owner) revert BadSignature();

        mandateId = keccak256(abi.encode(beneficiary, cap, expiry, nonce));
        nonce++;
        mandates[mandateId] = Mandate({
            beneficiary: beneficiary,
            cap: cap,
            spent: 0,
            expiry: expiry,
            active: true
        });
        emit MandateCreated(mandateId, beneficiary, cap, expiry);
    }

    function revokeMandate(bytes32 mandateId) external onlyOwner {
        if (mandates[mandateId].beneficiary == address(0)) revert MandateNotFound();
        mandates[mandateId].active = false;
        emit MandateRevoked(mandateId);
    }

    // ------------------------------------------------------- session keys
    /// @notice Registra uma session key com escopo restrito: vinculada a UM
    ///         mandato, com teto por pagamento e validade próprios.
    function registerSessionKey(
        address key,
        bytes32 mandateId,
        uint256 maxValue,
        uint256 expiry
    ) external onlyOwner {
        if (mandates[mandateId].beneficiary == address(0)) revert MandateNotFound();
        if (maxValue == 0) revert ZeroAmount();
        if (expiry <= block.timestamp) revert BadExpiry();
        sessionKeys[key] = SessionKey({
            mandateId: mandateId,
            maxValue: maxValue,
            expiry: expiry,
            active: true
        });
        emit SessionKeyRegistered(key, mandateId, maxValue, expiry);
    }

    function revokeSessionKey(address key) external onlyOwner {
        sessionKeys[key].active = false;
        emit SessionKeyRevoked(key);
    }

    // ------------------------------------------------------------------ cofre
    /// @notice Deposita tUSD8 no cofre (requer approve prévio do dono).
    function deposit(uint256 amount) external onlyOwner {
        if (amount == 0) revert ZeroAmount();
        if (!token.transferFrom(msg.sender, address(this), amount)) revert TransferFailed();
        emit Deposited(msg.sender, amount);
    }

    /// @notice Saque de emergência do dono (ex.: encerrar o protótipo).
    function withdraw(uint256 amount) external onlyOwner {
        if (amount == 0) revert ZeroAmount();
        if (token.balanceOf(address(this)) < amount) revert InsufficientVaultBalance();
        if (!token.transfer(owner, amount)) revert TransferFailed();
        emit Withdrawn(owner, amount);
    }

    // ------------------------------------------------- validação (sem estado)
    /// @notice Espelha TODAS as checagens de executePayment sem alterar
    ///         estado — a camada de segurança do backend chama isto via
    ///         eth_call ANTES de qualquer assinatura.
    function simulatePayment(
        address caller,
        bytes32 mandateId,
        uint256 amount
    ) external view returns (bool ok, string memory reason) {
        Mandate storage m = mandates[mandateId];
        if (m.beneficiary == address(0)) return (false, "mandate not found");
        if (!m.active) return (false, "mandate inactive");
        if (block.timestamp > m.expiry) return (false, "mandate expired");
        if (amount == 0) return (false, "zero amount");
        if (amount > m.cap - m.spent) return (false, "over mandate cap");
        if (caller != owner) {
            SessionKey storage sk = sessionKeys[caller];
            if (sk.mandateId == bytes32(0)) return (false, "session key not found");
            if (!sk.active) return (false, "session key inactive");
            if (block.timestamp > sk.expiry) return (false, "session key expired");
            if (sk.mandateId != mandateId) return (false, "session key bound to another mandate");
            if (amount > sk.maxValue) return (false, "over session key max value");
        }
        if (token.balanceOf(address(this)) < amount) return (false, "insufficient vault balance");
        return (true, "ok");
    }

    // ------------------------------------------------------------------ pagar
    /// @notice Executa um pagamento dentro do mandato. Pode ser chamado pelo
    ///         dono ou por uma session key válida. Fora do mandato = revert.
    function executePayment(bytes32 mandateId, uint256 amount) external {
        Mandate storage m = mandates[mandateId];
        if (m.beneficiary == address(0)) revert MandateNotFound();
        if (!m.active) revert MandateInactive();
        if (block.timestamp > m.expiry) revert MandateExpired();
        if (amount == 0) revert ZeroAmount();
        if (amount > m.cap - m.spent) revert OverMandateCap();
        if (msg.sender != owner) {
            SessionKey storage sk = sessionKeys[msg.sender];
            if (sk.mandateId == bytes32(0)) revert SessionKeyNotFound();
            if (!sk.active) revert SessionKeyInactive();
            if (block.timestamp > sk.expiry) revert SessionKeyExpired();
            if (sk.mandateId != mandateId) revert SessionKeyWrongMandate();
            if (amount > sk.maxValue) revert OverSessionKeyMax();
        }
        if (token.balanceOf(address(this)) < amount) revert InsufficientVaultBalance();

        m.spent += amount;
        if (!token.transfer(m.beneficiary, amount)) revert TransferFailed();
        emit PaymentExecuted(mandateId, msg.sender, m.beneficiary, amount);
    }

    // ------------------------------------------------------------- utilidades
    function _recover(bytes32 digest, bytes calldata signature) internal pure returns (address) {
        require(signature.length == 65, "bad sig length");
        bytes32 r;
        bytes32 s;
        uint8 v;
        assembly {
            r := calldataload(signature.offset)
            s := calldataload(add(signature.offset, 32))
            v := byte(0, calldataload(add(signature.offset, 64)))
        }
        if (v < 27) v += 27;
        return ecrecover(digest, v, r, s);
    }
}
