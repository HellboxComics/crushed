// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import "forge-std/Test.sol";
import { CrushedIt } from "../src/CrushedIt.sol";
import { Merkle } from "murky/Merkle.sol";

/// A stand-in for OpenSea's SeaDrop: the only thing the token sees from it is mintSeaDrop().
contract FakeSeaDrop {
    function mint(CrushedIt t, address to, uint256 q) external {
        t.mintSeaDrop(to, q);
    }
}

/// Same contract, with the offset settable so the shuffle can be checked for every value.
contract Harness is CrushedIt {
    constructor(address[] memory sd, bytes32 p, bytes32 c, bytes32 r, uint256 d, uint16[4] memory g, address roy)
        CrushedIt(sd, p, c, r, d, g, roy) {}

    function forceReveal(uint256 o) external {
        revealed = true;
        offset = o % SHUFFLED;
    }
}

contract CrushedItTest is Test {
    CrushedIt t;
    Harness h;
    FakeSeaDrop sd;
    Merkle m;

    address owner = address(0xA11CE);
    address team = address(0x7EA0);
    address[4] gifts = [address(0x101), address(0x102), address(0x103), address(0x104)];
    uint16[4] giftRecipes = [240, 718, 813, 796];
    bytes32 secret = keccak256("the secret nobody sees until reveal");
    bytes32 commit = keccak256(abi.encodePacked(keccak256("the secret nobody sees until reveal")));

    // a tiny fake collection for the seal tests: 8 recipes with made-up images and metadata
    bytes32[] leaves;
    bytes[] images;
    bytes[] metas;
    bytes32 root;

    function setUp() public {
        sd = new FakeSeaDrop();
        m = new Merkle();
        address[] memory allowed = new address[](1);
        allowed[0] = address(sd);
        for (uint256 r = 1; r <= 8; r++) {
            images.push(abi.encodePacked("JPEG", r, new bytes(30_000)));          // 30 KB, so it needs 2 chunks
            metas.push(abi.encodePacked('{"name":"CRUSHED IT #', vm.toString(r), '","attributes":[]'));
            leaves.push(keccak256(abi.encodePacked(uint256(r), sha256(images[r - 1]), keccak256(metas[r - 1]))));
        }
        root = m.getRoot(leaves);
        vm.startPrank(owner);
        t = new CrushedIt(allowed, keccak256("manifest"), commit, root, block.timestamp + 30 days, giftRecipes, owner);
        h = new Harness(allowed, keccak256("manifest"), commit, root, block.timestamp + 30 days, giftRecipes, owner);
        vm.stopPrank();
    }

    function _teamMint(CrushedIt c) internal {
        vm.prank(owner);
        c.mintTeam(team, gifts);
    }

    function _sellOut(CrushedIt c) internal {
        _teamMint(c);
        for (uint256 i = 0; i < 844; i++) {
            sd.mint(c, address(uint160(0x1000 + i)), 1);
        }
    }

    // -- fixed numbers --------------------------------------------------------------------------------

    function test_constants() public {
        assertEq(t.maxSupply(), 888);
        assertEq(t.name(), "CRUSHED IT");
        assertEq(t.symbol(), "CRUSHEDIT");
        assertEq(t.provenanceHash(), keccak256("manifest"));
        (address r, uint256 amt) = t.royaltyInfo(1, 10_000);
        assertEq(r, owner);
        assertEq(amt, 599);
    }

    // -- team and gifts -------------------------------------------------------------------------------

    function test_teamMintsFortyPlusGifts() public {
        _teamMint(t);
        assertEq(t.balanceOf(team), 40);
        for (uint256 i = 0; i < 4; i++) {
            assertEq(t.ownerOf(41 + i), gifts[i]);
            assertEq(t.recipeOf(41 + i), giftRecipes[i]);     // readable before the reveal
        }
        assertEq(t.totalSupply(), 44);
    }

    function test_teamCannotMintTwice() public {
        _teamMint(t);
        vm.prank(owner);
        vm.expectRevert(CrushedIt.TeamAlreadyMinted.selector);
        t.mintTeam(team, gifts);
    }

    function test_onlyOwnerMintsTeam() public {
        vm.prank(address(0xBAD));
        vm.expectRevert();
        t.mintTeam(address(0xBAD), gifts);
    }

    function test_publicWaitsForTeam() public {
        vm.expectRevert(CrushedIt.TeamMustMintFirst.selector);
        sd.mint(t, address(1), 1);
    }

    function test_onlySeaDropMints() public {
        _teamMint(t);
        vm.expectRevert();
        t.mintSeaDrop(address(this), 1);
    }

    function test_supplyCap() public {
        _sellOut(t);
        assertEq(t.totalSupply(), 888);
        vm.expectRevert();
        sd.mint(t, address(1), 1);
    }

    // -- reveal ---------------------------------------------------------------------------------------

    function test_revealNeedsSelloutOrDeadline() public {
        _teamMint(t);
        vm.expectRevert(CrushedIt.NotRevealable.selector);
        t.reveal(secret);
        vm.warp(block.timestamp + 31 days);
        t.reveal(secret);            // anyone, after the deadline
        assertTrue(t.revealed());
    }

    function test_revealBadSecret() public {
        _sellOut(t);
        vm.expectRevert(CrushedIt.BadSecret.selector);
        t.reveal(keccak256("wrong"));
    }

    function test_revealOnce() public {
        _sellOut(t);
        t.reveal(secret);
        vm.expectRevert(CrushedIt.AlreadyRevealed.selector);
        t.reveal(secret);
    }

    function test_recipeHiddenBeforeReveal() public {
        _teamMint(t);
        vm.expectRevert(CrushedIt.NotRevealed.selector);
        t.recipeOf(1);
        assertEq(t.recipeOf(41), 240);
    }

    function test_sealedURIBeforeReveal() public {
        _teamMint(t);
        vm.prank(owner);
        t.setSealedURI("ipfs://sealed");
        assertEq(t.tokenURI(1), "ipfs://sealed");
        vm.prank(owner);
        t.freezeURI();
        vm.prank(owner);
        vm.expectRevert(CrushedIt.Frozen.selector);
        t.setSealedURI("ipfs://other");
    }

    /// Every offset maps the 888 tokens onto the 888 recipes exactly once, gifts pinned.
    function testFuzz_shuffleIsABijection(uint256 o) public {
        _sellOut(h);
        h.forceReveal(o);
        bool[889] memory seen;
        for (uint256 id = 1; id <= 888; id++) {
            uint256 r = h.recipeOf(id);
            assertTrue(r >= 1 && r <= 888, "range");
            assertFalse(seen[r], "repeat");
            seen[r] = true;
        }
        for (uint256 i = 0; i < 4; i++) {
            assertEq(h.recipeOf(41 + i), giftRecipes[i]);
        }
        // no non-gift token ever lands on a gift recipe
        for (uint256 id = 1; id <= 888; id++) {
            if (id >= 41 && id <= 44) continue;
            uint256 r = h.recipeOf(id);
            for (uint256 i = 0; i < 4; i++) assertTrue(r != giftRecipes[i], "gift leaked");
        }
    }

    function test_offsetDependsOnBlockhash() public {
        _sellOut(t);
        uint256 snap = vm.snapshotState();
        vm.roll(block.number + 1);
        vm.prevrandao(bytes32(uint256(1)));
        t.reveal(secret);
        uint256 a = t.offset();
        vm.revertToState(snap);
        vm.roll(block.number + 7);
        t.reveal(secret);
        uint256 b = t.offset();
        assertTrue(a < 884 && b < 884);
    }

    // -- sealing --------------------------------------------------------------------------------------

    function _tokenFor(CrushedIt c, uint256 recipe) internal view returns (uint256) {
        for (uint256 id = 1; id <= 888; id++) {
            if (c.recipeOf(id) == recipe) return id;
        }
        revert("no token for recipe");
    }

    function _seal(CrushedIt c, uint256 id, uint256 recipe) internal {
        bytes memory img = images[recipe - 1];
        uint256 n = 0;
        for (uint256 off = 0; off < img.length; off += 24_000) {
            uint256 len = img.length - off < 24_000 ? img.length - off : 24_000;
            bytes memory chunk = new bytes(len);
            for (uint256 k = 0; k < len; k++) chunk[k] = img[off + k];
            c.sealChunk(id, n++, chunk);
        }
        c.sealFinish(id, metas[recipe - 1], m.getProof(leaves, recipe - 1));
    }

    function test_sealRoundTrip() public {
        _sellOut(h);
        h.forceReveal(5);
        uint256 id = _tokenFor(h, 3);
        assertFalse(h.isSealed(id));
        _seal(h, id, 3);
        assertTrue(h.isSealed(id));
        assertEq(keccak256(h.sealedImage(id)), keccak256(images[2]));
        string memory uri = h.tokenURI(id);
        assertEq(bytes(uri).length > 40_000, true);
        assertEq(_startsWith(uri, "data:application/json;base64,"), true);
    }

    function test_sealGiftBeforeReveal() public {
        _teamMint(h);                           // not revealed, but the gift's recipe is known
        vm.prank(gifts[0]);
        // gift 0 is recipe 240, outside our tiny tree, so the proof must fail; that is the point:
        bytes32[] memory proof = m.getProof(leaves, 0);
        h.sealChunk(41, 0, _head(images[0]));
        vm.expectRevert(CrushedIt.BadProof.selector);
        h.sealFinish(41, metas[0], proof);
    }

    function test_sealWrongImageFails() public {
        _sellOut(h);
        h.forceReveal(1);
        uint256 id = _tokenFor(h, 2);
        bytes32[] memory proof = m.getProof(leaves, 1);
        h.sealChunk(id, 0, _head(images[4]));   // recipe 5's picture on recipe 2's token
        vm.expectRevert(CrushedIt.BadProof.selector);
        h.sealFinish(id, metas[1], proof);
        assertFalse(h.isSealed(id));
    }

    function test_sealWrongMetaFails() public {
        _sellOut(h);
        h.forceReveal(1);
        uint256 id = _tokenFor(h, 2);
        bytes32[] memory proof = m.getProof(leaves, 1);
        h.sealChunk(id, 0, _head(images[1]));
        vm.expectRevert(CrushedIt.BadProof.selector);
        h.sealFinish(id, bytes('{"name":"forged"'), proof);
    }

    function test_sealOnlyOnce() public {
        _sellOut(h);
        h.forceReveal(9);
        uint256 id = _tokenFor(h, 7);
        _seal(h, id, 7);
        vm.expectRevert(CrushedIt.AlreadySealed.selector);
        h.sealChunk(id, 0, images[6]);
    }

    function test_sealChunkOrder() public {
        _sellOut(h);
        h.forceReveal(2);
        uint256 id = _tokenFor(h, 1);
        bytes32[] memory proof = m.getProof(leaves, 0);
        bytes memory head = _head(images[0]);
        vm.expectRevert(CrushedIt.NothingPending.selector);
        h.sealChunk(id, 1, head);               // index 1 before index 0
        vm.expectRevert(CrushedIt.NothingPending.selector);
        h.sealFinish(id, metas[0], proof);
        vm.expectRevert(CrushedIt.ChunkTooBig.selector);
        h.sealChunk(id, 0, new bytes(24_001));
    }

    function test_sealBeforeRevealFails() public {
        _teamMint(t);
        vm.expectRevert(CrushedIt.NotRevealed.selector);
        t.sealChunk(1, 0, images[0]);
    }

    function test_restartUploadWithIndexZero() public {
        _sellOut(h);
        h.forceReveal(3);
        uint256 id = _tokenFor(h, 4);
        h.sealChunk(id, 0, _head(images[6]));   // wrong start
        _seal(h, id, 4);                        // restarts at 0 and succeeds
        assertTrue(h.isSealed(id));
    }

    function test_erc4906Interface() public view {
        assertTrue(t.supportsInterface(0x49064906));
        assertTrue(t.supportsInterface(0x80ac58cd));   // ERC-721
        assertTrue(t.supportsInterface(0x2a55205a));   // ERC-2981
    }

    function _head(bytes memory b) internal pure returns (bytes memory out) {
        out = new bytes(24_000);
        for (uint256 i = 0; i < 24_000; i++) out[i] = b[i];
    }

    function _startsWith(string memory s, string memory p) internal pure returns (bool) {
        bytes memory a = bytes(s);
        bytes memory b = bytes(p);
        if (a.length < b.length) return false;
        for (uint256 i = 0; i < b.length; i++) if (a[i] != b[i]) return false;
        return true;
    }
}
