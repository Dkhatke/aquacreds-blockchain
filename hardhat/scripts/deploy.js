  // hardhat/scripts/deploy.js
const { ethers } = require("hardhat");

async function main() {
  // get deployer wallet
  const [deployer] = await ethers.getSigners();
  console.log("Deploying contracts with:", deployer.address);

  // 1. Deploy ProjectRegistry (NO CONSTRUCTOR ARGS)
  const ProjectRegistry = await ethers.getContractFactory("ProjectRegistry");
  const registry = await ProjectRegistry.deploy();
  await registry.deployed();
  console.log("ProjectRegistry deployed at:", registry.address);

  // 2. Deploy Verification WITH REQUIRED 2 ARGS
  //    (registryAddress, verifierAddress)
  const verifierAddress = deployer.address;  // your Metamask account as verifier

  const Verification = await ethers.getContractFactory("Verification");
  const verification = await Verification.deploy(
    registry.address,
    verifierAddress
  );
  await verification.deployed();
  console.log("Verification deployed at:", verification.address);

  // 3. Deploy CarbonCreditToken (ONE ARG: verificationAddress)
  const CarbonCreditToken = await ethers.getContractFactory("CarbonCreditToken");
  const token = await CarbonCreditToken.deploy(verification.address);
  await token.deployed();
  console.log("CarbonCreditToken deployed at:", token.address);

  // 4. Deploy Marketplace (ONE ARG: tokenAddress)
  const Marketplace = await ethers.getContractFactory("Marketplace");
  const marketplace = await Marketplace.deploy(token.address);
  await marketplace.deployed();
  console.log("Marketplace deployed at:", marketplace.address);
}

main()
  .then(() => process.exit(0))
  .catch((error) => {
    console.error(error);
    process.exit(1);
  });
