// SPDX-License-Identifier: MIT
pragma solidity ^0.8.19;

import "./ReverseAuction.sol";

contract AuctionFactory {
    address[] public allAuctions;

    event AuctionCreated(
        address indexed auction,
        address indexed creator,
        string auctionId
    );

    function createAuction(
        string memory auctionId,
        address paymentToken,
        uint256 requiredQuantity,
        uint256 maxPricePerTon,
        uint256 deadline
    ) external returns (address) {
        ReverseAuction a = new ReverseAuction(
            auctionId,
            msg.sender,
            paymentToken,
            requiredQuantity,
            maxPricePerTon,
            deadline
        );
        allAuctions.push(address(a));
        emit AuctionCreated(address(a), msg.sender, auctionId);
        return address(a);
    }

    function getAuctions() external view returns (address[] memory) {
        return allAuctions;
    }
}
