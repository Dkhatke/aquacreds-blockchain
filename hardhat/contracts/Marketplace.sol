// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./CarbonCreditToken.sol";

contract Marketplace {
    CarbonCreditToken public token;

    address public admin;
    uint256 public marketplaceFeePercentage = 2; // 2% marketplace fee

    struct Listing {
        address seller;
        uint256 amount;     // amount of BCC tokens for sale
        uint256 price;      // price in wei (MATIC/ETH) for 1 BCC token
        bool active;
    }

    mapping(uint256 => Listing) public listings;
    uint256 public listingCounter;

    event TokensListed(uint256 indexed listingId, address indexed seller, uint256 amount, uint256 price);
    event ListingUpdated(uint256 indexed listingId, uint256 newPrice);
    event ListingCanceled(uint256 indexed listingId);
    event TokensPurchased(uint256 indexed listingId, address indexed buyer, uint256 totalPaid, uint256 tokensBought);

    modifier onlyAdmin() {
        require(msg.sender == admin, "Not admin");
        _;
    }

    constructor(address tokenAddress) {
        require(tokenAddress != address(0), "Invalid token address");
        token = CarbonCreditToken(tokenAddress);
        admin = msg.sender;
    }

    //-------------------------------------------
    // LIST TOKENS FOR SALE
    //-------------------------------------------
    function listTokens(uint256 amount, uint256 price) external returns (uint256) {
        require(amount > 0, "Amount must be > 0");
        require(price > 0, "Price must be > 0");

        // Marketplace must be approved to transfer tokens
        require(
            token.allowance(msg.sender, address(this)) >= amount,
            "Marketplace not approved to transfer tokens"
        );

        listingCounter++;
        listings[listingCounter] = Listing({
            seller: msg.sender,
            amount: amount,
            price: price,
            active: true
        });

        emit TokensListed(listingCounter, msg.sender, amount, price);
        return listingCounter;
    }

    //-------------------------------------------
    // UPDATE PRICE
    //-------------------------------------------
    function updatePrice(uint256 listingId, uint256 newPrice) external {
        Listing storage list = listings[listingId];
        require(list.active, "Listing not active");
        require(msg.sender == list.seller, "Not the seller");
        require(newPrice > 0, "Price must be > 0");

        list.price = newPrice;
        emit ListingUpdated(listingId, newPrice);
    }

    //-------------------------------------------
    // CANCEL LISTING
    //-------------------------------------------
    function cancelListing(uint256 listingId) external {
        Listing storage list = listings[listingId];
        require(list.active, "Already inactive");
        require(msg.sender == list.seller, "Not the seller");

        list.active = false;

        emit ListingCanceled(listingId);
    }

    //-------------------------------------------
    // BUY TOKENS
    //-------------------------------------------
    function buyTokens(uint256 listingId, uint256 amountToBuy) external payable {
        Listing storage list = listings[listingId];

        require(list.active, "Listing inactive");
        require(amountToBuy > 0, "Invalid amount");
        require(amountToBuy <= list.amount, "Not enough tokens available");
        require(msg.sender != list.seller, "Cannot buy your own tokens");

        uint256 totalCost = amountToBuy * list.price;
        require(msg.value == totalCost, "Incorrect payment amount");

        // Marketplace fee
        uint256 fee = (totalCost * marketplaceFeePercentage) / 100;
        uint256 sellerAmount = totalCost - fee;

        // Pay seller
        payable(list.seller).transfer(sellerAmount);

        // Pay marketplace fee to admin
        payable(admin).transfer(fee);

        // Transfer tokens to buyer
        token.transferFrom(list.seller, msg.sender, amountToBuy);

        // Reduce listing supply
        list.amount -= amountToBuy;

        // Deactivate if fully sold
        if (list.amount == 0) {
            list.active = false;
        }

        emit TokensPurchased(listingId, msg.sender, totalCost, amountToBuy);
    }

    //-------------------------------------------
    // ADMIN: UPDATE MARKETPLACE FEE
    //-------------------------------------------
    function updateMarketplaceFee(uint256 newFee) external onlyAdmin {
        require(newFee <= 10, "Cannot exceed 10%");
        marketplaceFeePercentage = newFee;
    }

    //-------------------------------------------
    // ADMIN: CHANGE ADMIN ADDRESS
    //-------------------------------------------
    function changeAdmin(address newAdmin) external onlyAdmin {
        admin = newAdmin;
    }
}