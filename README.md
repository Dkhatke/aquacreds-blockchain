
# AquaCreds Blockchain Layer

This repository contains the **smart contracts and blockchain infrastructure** for the **AquaCreds Blue Carbon Registry System**, developed for **Smart India Hackathon 2025 (SIH25038)**.

The blockchain layer ensures **transparency, immutability, and trust** in the **Monitoring, Reporting, and Verification (MRV)** process for blue carbon ecosystems such as **mangroves, seagrass, and marshlands**.

The system records verified carbon data on the **Polygon blockchain** and enables **tokenized carbon credit issuance and trading**. 

---

# Overview

Traditional carbon credit systems suffer from:

* Manual verification processes
* Lack of transparency
* Risk of data manipulation
* Delayed carbon credit issuance

The AquaCreds blockchain layer solves this by storing **hashes of verified MRV reports on-chain**, ensuring that records cannot be altered after verification.

---

# Key Components

## Smart Contracts

The blockchain implementation consists of the following smart contracts:

### 1. MRV Registry Contract

Stores hashes of verified MRV records.

Functions:

* Register MRV report hash
* Retrieve MRV record
* Verify report authenticity

Each record represents:

* Plantation location
* Carbon estimation
* Verification status
* Timestamp

---

### 2. Carbon Credit Token Contract (ERC-20)

This contract issues **tokenized carbon credits**.

Each token represents a **verified carbon offset unit (tCO₂e)**.

Functions include:

* Mint carbon credits after approval
* Transfer credits between users
* Track carbon credit supply

---

### 3. Plantation NFT Contract (ERC-721)

Each plantation or restoration project is represented as a **unique NFT**.

This ensures:

* Traceability of projects
* Unique ownership records
* Linking MRV reports to specific ecosystems

---

# Blockchain Architecture

```id="blockchain_arch"
Field Data Verified
        │
        ▼
MRV Report Generated
        │
        ▼
Hash Stored on IPFS
        │
        ▼
IPFS Hash Recorded on Polygon Blockchain
        │
        ▼
Smart Contract Verification
        │
        ▼
Carbon Credits Minted (ERC20)
        │
        ▼
Plantation NFT Linked (ERC721)
```

---

# Tech Stack

Blockchain Framework

* **Solidity**
* **Hardhat**

Blockchain Network

* **Polygon**

Libraries

* **OpenZeppelin**

Wallet Integration

* **MetaMask**

Web3 Interaction

* **Ethers.js / Web3.js**



---


# Smart Contract Workflow

### Step 1 — MRV Verification

1. AI and satellite analysis verify plantation data.
2. Final MRV report is generated.

---

### Step 2 — Hash Generation

The report is stored in **IPFS**.

```
MRV Report → IPFS → Hash Generated
```

---

### Step 3 — Blockchain Recording

The **IPFS hash is stored in the MRVRegistry smart contract**.

This ensures:

* Data integrity
* Permanent record
* Auditability

---

### Step 4 — Carbon Credit Issuance

After approval:

* Carbon credits are **minted as ERC-20 tokens**
* Tokens represent verified **tCO₂e offsets**

---

### Step 5 — NFT Linking

A **Plantation NFT** links:

* Location
* MRV records
* Carbon credits issued

This ensures **traceable ecosystem projects**.

---

# Installation

Clone the repository:

```
git clone https://github.com/your-username/aquacreds-blockchain
cd aquacreds-blockchain
```

Install dependencies:

```
npm install
```

---

# Compile Contracts

```
npx hardhat compile
```

---

# Run Tests

```
npx hardhat test
```

---

# Deploy Smart Contracts

```
npx hardhat run scripts/deploy.js --network polygon
```

---

# Environment Variables

Create a `.env` file:

```
PRIVATE_KEY=your_wallet_private_key
POLYGON_RPC_URL=your_polygon_rpc
```

---

# Security Considerations

The blockchain layer ensures security through:

* Immutable smart contract storage
* OpenZeppelin audited libraries
* Decentralized IPFS storage
* Transparent carbon credit minting

---

# Future Enhancements

* DAO governance for carbon credit validation
* Automated oracle-based satellite verification
* Cross-chain carbon credit trading
* Integration with global carbon markets



That version will make your **GitHub repo look very professional for recruiters and SIH judges.**

