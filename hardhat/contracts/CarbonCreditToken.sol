// SPDX-License-Identifier: MIT
//CarbonCreditToken.sol
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "./Verification.sol";

contract CarbonCreditToken is ERC20 {
    Verification public verificationContract;
    address public admin;      // Only admin mints credits

    mapping(string => bool) public creditsIssued;

    event CreditsMinted(string indexed projectId, address indexed ngo, uint256 amount);

    constructor(address verificationAddress) ERC20("BlueCarbonCredit", "BCC") {
        require(verificationAddress != address(0), "Invalid verification address");
        verificationContract = Verification(verificationAddress);
        admin = msg.sender;
    }

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    /**
     * @notice Mint carbon credits to NGO after verification and lock period.
     * @param projectId Project identifier
     * @param ngo Address of the NGO receiver
     * @param amount Amount of tokens (representing tCO2e or scaled units)
     */
    function mintCredits(
        string calldata projectId,
        address ngo,
        uint256 amount
    ) external onlyAdmin {
        require(!creditsIssued[projectId], "Credits already issued for this project");
        require(verificationContract.isEligible(projectId), "Project not eligible for credits");

        creditsIssued[projectId] = true;
        _mint(ngo, amount);

        emit CreditsMinted(projectId, ngo, amount);
    }

    /**
     * @notice Admin can change admin if needed (optional).
     * @param newAdmin New admin address
     */
    function setAdmin(address newAdmin) external onlyAdmin {
        require(newAdmin != address(0), "Invalid new admin");
        admin = newAdmin;
    }
}