// SPDX-License-Identifier: MIT
//Verification.sol
pragma solidity ^0.8.19;

import "./ProjectRegistry.sol";

contract Verification {
    ProjectRegistry public registry;
    address public verifier;     // single authorized verifier address

    uint256 public constant LOCK_PERIOD = 365 days;  // 1-year wait before credits can be minted

    struct MRVData {
        string projectId;
        string mrvHash;
        uint256 submittedAt;
        bool approved;
        uint256 approvedAt;
        bool exists;
    }

    mapping(string => MRVData) private verifications;

    event MRVSubmitted(string indexed projectId, string mrvHash, uint256 submittedAt);
    event MRVApproved(string indexed projectId, uint256 approvedAt);
    event MRVRejected(string indexed projectId);

    constructor(address registryAddress, address verifierAddress) {
        require(registryAddress != address(0), "Invalid registry address");
        require(verifierAddress != address(0), "Invalid verifier address");
        registry = ProjectRegistry(registryAddress);
        verifier = verifierAddress;
    }

    modifier onlyVerifier() {
        require(msg.sender == verifier, "Not authorized verifier");
        _;
    }

    /**
     * @notice Submit MRV/ML result hash for a registered project. Callable only by verifier.
     * @param projectId Project identifier (must be registered)
     * @param mrvHash Hash of ML/MRV JSON stored off-chain (NDVI, AGB, BGB, etc.)
     */
    function submitMRV(string calldata projectId, string calldata mrvHash) external onlyVerifier {
        require(registry.projectExists(projectId), "Project not registered");

        verifications[projectId] = MRVData({
            projectId: projectId,
            mrvHash: mrvHash,
            submittedAt: block.timestamp,
            approved: false,
            approvedAt: 0,
            exists: true
        });

        emit MRVSubmitted(projectId, mrvHash, block.timestamp);
    }

    /**
     * @notice Approve MRV data for the given project. Starts the lock period.
     * @param projectId Project identifier
     */
    function approveMRV(string calldata projectId) external onlyVerifier {
        require(verifications[projectId].exists, "MRV not submitted");

        MRVData storage m = verifications[projectId];
        m.approved = true;
        m.approvedAt = block.timestamp;

        emit MRVApproved(projectId, block.timestamp);
    }

    /**
     * @notice Reject MRV submission (keeps approved=false).
     * @param projectId Project identifier
     */
    function rejectMRV(string calldata projectId) external onlyVerifier {
        require(verifications[projectId].exists, "MRV not submitted");

        MRVData storage m = verifications[projectId];
        m.approved = false;
        m.approvedAt = 0;

        emit MRVRejected(projectId);
    }

    /**
     * @notice Check eligibility: MRV approved and lock period passed.
     * @param projectId Project identifier
     */
    function isEligible(string calldata projectId) external view returns (bool) {
        MRVData memory m = verifications[projectId];
        if (!m.exists) return false;
        if (!m.approved) return false;
        return block.timestamp >= m.approvedAt + LOCK_PERIOD;
    }

    /**
     * @notice Get MRV info (hash and approval state)
     * @param projectId Project identifier
     */
    function getMRV(string calldata projectId)
        external
        view
        returns (
            string memory mrvHash,
            uint256 submittedAt,
            bool approved,
            uint256 approvedAt
        )
    {
        require(verifications[projectId].exists, "MRV not submitted");
        MRVData memory m = verifications[projectId];
        return (m.mrvHash, m.submittedAt, m.approved, m.approvedAt);
    }
}