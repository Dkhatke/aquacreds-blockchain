// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

contract ReverseAuction is ReentrancyGuard {
    string public auctionId;
    address public buyer;
    IERC20 public paymentToken;

    uint256 public requiredQuantity;
    uint256 public maxPricePerTon;
    uint256 public deadline;

    bool public finalized;

    uint256 public constant QUANTITY_SCALE = 1e18;

    struct Bid {
        uint256 id;
        address bidder;
        string projectId;
        uint256 pricePerTon;
        uint256 quantity;
        bool exists;
        bool awarded;
    }

    uint256 public nextBidId;
    mapping(uint256 => Bid) public bids;
    uint256[] public bidIds;

    mapping(address => uint256) public pendingWithdrawals;
    uint256 public escrowedAmount;

    event BidSubmitted(uint256 indexed bidId, address indexed bidder, string projectId, uint256 pricePerTon, uint256 quantity);
    event AuctionFinalized(uint256 totalPaid);
    event PaymentScheduled(uint256 indexed bidId, address indexed to, uint256 amount);
    event WithdrawalClaimed(address indexed who, uint256 amount);

    modifier onlyBuyer() {
        require(msg.sender == buyer, "Only buyer");
        _;
    }

    constructor(
        string memory _auctionId,
        address _buyer,
        address _paymentToken,
        uint256 _requiredQuantity,
        uint256 _maxPricePerTon,
        uint256 _deadline
    ) {
        require(_deadline > block.timestamp, "deadline passed");
        auctionId = _auctionId;
        buyer = _buyer;
        paymentToken = IERC20(_paymentToken);
        requiredQuantity = _requiredQuantity;
        maxPricePerTon = _maxPricePerTon;
        deadline = _deadline;
        nextBidId = 1;
    }

    function depositEscrow(uint256 amount) external onlyBuyer {
        require(amount > 0, "zero");
        bool ok = paymentToken.transferFrom(msg.sender, address(this), amount);
        require(ok, "transfer failed");
        escrowedAmount += amount;
    }

    function submitBid(string calldata projectId, uint256 pricePerTon, uint256 quantity) external nonReentrant {
        require(block.timestamp < deadline, "auction closed");
        require(pricePerTon <= maxPricePerTon, "price > max");
        require(quantity > 0, "zero quantity");

        uint256 id = nextBidId++;

        bids[id] = Bid({
            id: id,
            bidder: msg.sender,
            projectId: projectId,
            pricePerTon: pricePerTon,
            quantity: quantity,
            exists: true,
            awarded: false
        });

        bidIds.push(id);

        emit BidSubmitted(id, msg.sender, projectId, pricePerTon, quantity);
    }

    function finalizeAuction(uint256[] calldata winnerBidIds) external nonReentrant onlyBuyer {
        require(block.timestamp >= deadline, "still open");
        require(!finalized, "already finalized");

        uint256 totalQuantity = 0;
        uint256 totalPayment = 0;

        for (uint256 i = 0; i < winnerBidIds.length; i++) {
            uint256 bidId = winnerBidIds[i];
            Bid storage b = bids[bidId];

            require(b.exists, "invalid bid");
            require(!b.awarded, "already awarded");

            totalQuantity += b.quantity;
            uint256 pay = (b.pricePerTon * b.quantity) / QUANTITY_SCALE;
            totalPayment += pay;
        }

        require(totalQuantity >= requiredQuantity, "insufficient quantity selected");

        if (escrowedAmount < totalPayment) {
            uint256 need = totalPayment - escrowedAmount;
            bool ok = paymentToken.transferFrom(msg.sender, address(this), need);
            require(ok, "transfer failed");
            escrowedAmount += need;
        }

        for (uint256 i = 0; i < winnerBidIds.length; i++) {
            uint256 bidId = winnerBidIds[i];
            Bid storage b = bids[bidId];

            b.awarded = true;

            uint256 pay = (b.pricePerTon * b.quantity) / QUANTITY_SCALE;

            escrowedAmount -= pay;
            pendingWithdrawals[b.bidder] += pay;

            emit PaymentScheduled(bidId, b.bidder, pay);
        }

        finalized = true;
        emit AuctionFinalized(totalPayment);
    }

    function claim() external nonReentrant {
        uint256 amt = pendingWithdrawals[msg.sender];
        require(amt > 0, "no funds");
        pendingWithdrawals[msg.sender] = 0;

        bool ok = paymentToken.transfer(msg.sender, amt);
        require(ok, "transfer failed");

        emit WithdrawalClaimed(msg.sender, amt);
    }

    function getBidIds() external view returns (uint256[] memory) {
        return bidIds;
    }

    function getBid(uint256 bidId) external view returns (Bid memory) {
        return bids[bidId];
    }

    function withdrawEscrow(uint256 amount) external onlyBuyer {
        require(amount <= escrowedAmount, "insufficient");
        escrowedAmount -= amount;

        bool ok = paymentToken.transfer(msg.sender, amount);
        require(ok, "transfer failed");
    }
}
