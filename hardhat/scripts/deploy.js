const hre = require("hardhat");

async function main() {
  const [deployer] = await hre.ethers.getSigners();
  console.log("Deploying with address:", deployer.address);

  // Deploy ProjectRegistry
  const Registry = await hre.ethers.getContractFactory("ProjectRegistry");
  const registry = await Registry.deploy();
  await registry.deployed();
  console.log("ProjectRegistry deployed at:", registry.address);

  // Deploy Verification
  const Verification = await hre.ethers.getContractFactory("Verification");
  const verification = await Verification.deploy(
    registry.address,
    deployer.address
  );
  await verification.deployed();
  console.log("Verification deployed at:", verification.address);

  // Deploy CarbonCreditToken
  const Token = await hre.ethers.getContractFactory("CarbonCreditToken");
  const token = await Token.deploy(verification.address);
  await token.deployed();
  console.log("CarbonCreditToken deployed at:", token.address);

  // Deploy Marketplace
  const Marketplace = await hre.ethers.getContractFactory("Marketplace");
  const marketplace = await Marketplace.deploy(token.address);
  await marketplace.deployed();
  console.log("Marketplace deployed at:", marketplace.address);

  console.log("\n🎉 All contracts deployed successfully!");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
