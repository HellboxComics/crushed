// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import "forge-std/Script.sol";
import { CrushedIt } from "../src/CrushedIt.sol";

/// Deploy CRUSHED IT. Nothing here runs without Harrow's explicit go, testnet first.
///
///   PROVENANCE=0x..   sha256 of collection/manifest.json (collection/provenance.txt)
///   REVEAL_COMMIT=0x..   keccak256(abi.encodePacked(secret)); keep the secret offline until reveal
///   IMAGE_ROOT=0x..   root from collection/sealed.json (scripts/seal_tree.py build)
///   REVEAL_DEADLINE=  unix time after which anyone can reveal even if not sold out
///   ROYALTY_TO=0x..   where the 5.99% goes
///   SEADROP=0x00005EA00Ac477B1030CE78506496e8C2dE24bf5   (verified live on Robinhood Chain)
///
///   forge script script/Deploy.s.sol --rpc-url robinhood_testnet --broadcast --verify
contract Deploy is Script {
    function run() external {
        address[] memory allowed = new address[](1);
        allowed[0] = vm.envAddress("SEADROP");
        uint16[4] memory gifts = [uint16(240), 718, 813, 796];   // LOW RES, CCFF00, STOP THE PRESSES, CLAY DAY
        vm.startBroadcast();
        CrushedIt c = new CrushedIt(
            allowed,
            vm.envBytes32("PROVENANCE"),
            vm.envBytes32("REVEAL_COMMIT"),
            vm.envBytes32("IMAGE_ROOT"),
            vm.envUint("REVEAL_DEADLINE"),
            gifts,
            vm.envAddress("ROYALTY_TO")
        );
        vm.stopBroadcast();
        console.log("CRUSHED IT at", address(c));
    }
}
