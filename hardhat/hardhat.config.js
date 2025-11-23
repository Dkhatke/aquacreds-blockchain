require("@nomicfoundation/hardhat-toolbox");
require("dotenv").config();

const RPC_URL = process.env.RPC_URL;
const ADMIN_PRIVATE_KEY = process.env.ADMIN_PRIVATE_KEY;
const VERIFIER_ADDRESS = process.env.VERIFIER_ADDRESS;

module.exports = {
  solidity: "0.8.20",
  networks: {
    amoy: {
      url: RPC_URL,
      accounts: [ADMIN_PRIVATE_KEY]
    }
  }
};
