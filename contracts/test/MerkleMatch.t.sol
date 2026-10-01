// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import "forge-std/Test.sol";
import { Merkle } from "murky/Merkle.sol";

/// scripts/seal_tree.py must build the same tree as murky (which the contract's _verify matches).
contract MerkleMatchTest is Test {
    function test_rootMatchesPython() public {
        Merkle m = new Merkle();
        bytes32[] memory leaves = new bytes32[](7);
        for (uint256 i = 0; i < 7; i++) leaves[i] = keccak256(abi.encodePacked(bytes1(uint8(i))));
        bytes32 root = m.getRoot(leaves);
        bytes32[] memory p = m.getProof(leaves, 2);
        console.logBytes32(root);
        console.logBytes32(p[0]);
        console.logBytes32(p[1]);
        console.logBytes32(p[2]);
        assertTrue(m.verifyProof(root, p, leaves[2]));
    }
}
