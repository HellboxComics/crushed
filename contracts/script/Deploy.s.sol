// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Script, console2} from "forge-std/Script.sol";
import {Crushed} from "../src/Crushed.sol";

/// forge script script/Deploy.s.sol --rpc-url robinhood_testnet --broadcast --verify
contract Deploy is Script {
    function run() external returns (Crushed c) {
        address owner = vm.envAddress("OWNER");
        bytes32 provenance = vm.envBytes32("PROVENANCE");
        bytes32 revealCommit = vm.envBytes32("REVEAL_COMMIT");
        uint256 price = vm.envOr("PRICE_WEI", uint256(0));
        uint256 maxPerWallet = vm.envOr("MAX_PER_WALLET", uint256(8));
        string memory sealedURI = vm.envString("SEALED_URI");
        string memory contractURI = vm.envString("CONTRACT_URI");
        address royaltyReceiver = vm.envOr("ROYALTY_RECEIVER", owner);
        uint96 royaltyBps = uint96(vm.envOr("ROYALTY_BPS", uint256(500)));

        vm.startBroadcast();
        c = new Crushed(
            owner, provenance, revealCommit, price, maxPerWallet, sealedURI, contractURI, royaltyReceiver, royaltyBps
        );
        vm.stopBroadcast();
        console2.log("CRUSHED deployed at", address(c));
    }
}
