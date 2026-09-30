// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {Test} from "forge-std/Test.sol";
import {Crushed} from "../src/Crushed.sol";

contract CrushedTest is Test {
    Crushed c;
    address owner = address(0xB0B);
    address alice = address(0xA11CE);
    address bob = address(0xB0BB);
    bytes32 secret = keccak256("we kept the important shit");
    bytes32 provenance = 0x65b64e95ef3e5b5213845479b539b344229f25dfb391deeaac7e9e361280d82f;
    uint256 price = 0.0088 ether;

    function setUp() public {
        c = new Crushed(
            owner, provenance, keccak256(abi.encodePacked(secret)), price, 8, "ipfs://sealed.json",
            "ipfs://contract.json", owner, 500
        );
        vm.deal(alice, 10 ether);
        vm.deal(bob, 10 ether);
    }

    function _open() internal {
        vm.prank(owner);
        c.setMintOpen(true);
    }

    function test_nameAndSupply() public view {
        assertEq(c.name(), "CRUSHED");
        assertEq(c.symbol(), "CRUSHED");
        assertEq(c.MAX_SUPPLY(), 888);
        assertEq(c.PROVENANCE(), provenance);
    }

    function test_mintClosedByDefault() public {
        vm.prank(alice);
        vm.expectRevert(Crushed.MintClosed.selector);
        c.mint{value: price}(1);
    }

    function test_mint() public {
        _open();
        vm.prank(alice);
        c.mint{value: price * 3}(3);
        assertEq(c.balanceOf(alice), 3);
        assertEq(c.ownerOf(1), alice);
        assertEq(c.ownerOf(3), alice);
        assertEq(c.totalMinted(), 3);
        assertEq(address(c).balance, price * 3);
    }

    function test_wrongPrice() public {
        _open();
        vm.prank(alice);
        vm.expectRevert(Crushed.WrongPrice.selector);
        c.mint{value: price}(2);
    }

    function test_zeroQuantity() public {
        _open();
        vm.prank(alice);
        vm.expectRevert(Crushed.BadQuantity.selector);
        c.mint{value: 0}(0);
    }

    function test_walletLimit() public {
        _open();
        vm.startPrank(alice);
        c.mint{value: price * 8}(8);
        vm.expectRevert(Crushed.WalletLimit.selector);
        c.mint{value: price}(1);
        vm.stopPrank();
    }

    function test_supplyCap() public {
        vm.startPrank(owner);
        c.ownerMint(owner, 880);
        c.setMintOpen(true);
        vm.stopPrank();
        vm.prank(alice);
        c.mint{value: price * 8}(8);
        assertEq(c.totalMinted(), 888);
        vm.prank(bob);
        vm.expectRevert(Crushed.SoldOut.selector);
        c.mint{value: price}(1);
        vm.prank(owner);
        vm.expectRevert(Crushed.SoldOut.selector);
        c.ownerMint(owner, 1);
    }

    function test_onlyOwnerAdmin() public {
        vm.startPrank(alice);
        vm.expectRevert();
        c.setMintOpen(true);
        vm.expectRevert();
        c.ownerMint(alice, 1);
        vm.expectRevert();
        c.reveal(secret);
        vm.expectRevert();
        c.setBaseURI("x");
        vm.expectRevert();
        c.withdraw(payable(alice));
        vm.stopPrank();
    }

    function test_sealedUntilReveal() public {
        _open();
        vm.prank(alice);
        c.mint{value: price}(1);
        vm.prank(owner);
        c.setBaseURI("ipfs://meta/");
        assertEq(c.tokenURI(1), "ipfs://sealed.json");
    }

    function test_revealRequiresClosedMintAndSecret() public {
        _open();
        vm.prank(alice);
        c.mint{value: price}(1);
        vm.startPrank(owner);
        vm.expectRevert(Crushed.NotRevealable.selector);
        c.reveal(secret);
        c.setMintOpen(false);
        vm.expectRevert(Crushed.BadSecret.selector);
        c.reveal(keccak256("wrong"));
        vm.roll(100);
        c.reveal(secret);
        vm.expectRevert(Crushed.AlreadyRevealed.selector);
        c.reveal(secret);
        vm.expectRevert(Crushed.AlreadyRevealed.selector);
        c.setMintOpen(true);
        vm.stopPrank();
        assertTrue(c.revealed());
        assertLt(c.offset(), 888);
    }

    function test_revealedURIAndRecipe() public {
        vm.startPrank(owner);
        c.ownerMint(alice, 888);
        vm.roll(500);
        c.reveal(secret);
        c.setBaseURI("ipfs://meta/");
        vm.stopPrank();
        assertEq(c.tokenURI(44), "ipfs://meta/44");
        uint256 o = c.offset();
        assertEq(c.recipeOf(1), (o % 888) + 1);
        // the mapping is a permutation of 1..888
        bool[889] memory seen;
        for (uint256 t = 1; t <= 888; ++t) {
            uint256 r = c.recipeOf(t);
            assertTrue(r >= 1 && r <= 888);
            assertFalse(seen[r]);
            seen[r] = true;
        }
    }

    function test_freeze() public {
        vm.startPrank(owner);
        c.freezeMetadata();
        vm.expectRevert(Crushed.Frozen.selector);
        c.setBaseURI("ipfs://other/");
        vm.expectRevert(Crushed.Frozen.selector);
        c.setSealedURI("ipfs://other.json");
        vm.stopPrank();
    }

    function test_royaltyAndInterfaces() public view {
        (address recv, uint256 amt) = c.royaltyInfo(1, 1 ether);
        assertEq(recv, owner);
        assertEq(amt, 0.05 ether);
        assertTrue(c.supportsInterface(0x80ac58cd)); // ERC-721
        assertTrue(c.supportsInterface(0x2a55205a)); // ERC-2981
        assertTrue(c.supportsInterface(0x49064906)); // ERC-4906
    }

    function test_withdraw() public {
        _open();
        vm.prank(alice);
        c.mint{value: price * 2}(2);
        uint256 before = owner.balance;
        vm.prank(owner);
        c.withdraw(payable(owner));
        assertEq(owner.balance - before, price * 2);
        assertEq(address(c).balance, 0);
    }

    function testFuzz_mintQuantities(uint8 q) public {
        uint256 quantity = bound(q, 1, 8);
        _open();
        vm.prank(bob);
        c.mint{value: price * quantity}(quantity);
        assertEq(c.balanceOf(bob), quantity);
        assertEq(c.mintedBy(bob), quantity);
    }
}
