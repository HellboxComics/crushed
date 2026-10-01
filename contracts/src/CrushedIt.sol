// SPDX-License-Identifier: MIT
pragma solidity 0.8.17;

import { ERC721SeaDrop } from "seadrop/ERC721SeaDrop.sol";
import { SSTORE2 } from "solmate/utils/SSTORE2.sol";

/// @title CRUSHED IT
/// @notice 888 twelve-inch cubes of crushed nostalgic junk, on Robinhood Chain.
///
/// @dev The art is fixed before mint: `provenanceHash()` is sha256 of collection/manifest.json (every recipe,
///      every trait, every drop-in art file). IMAGE_ROOT is a Merkle root over (recipeId, sha256(image),
///      keccak256(metadata)), so a holder can pay to put their block on-chain and the contract can prove it
///      is the real one.
///
///      Which token gets which recipe is decided by `reveal()` after the mint closes, with a secret committed
///      at deploy plus a block hash nobody controls, so no mint can be aimed at a one-of-one. The four gift
///      blocks are the exception: token ids 41 to 44 are pinned to their recipes and minted to the people
///      they were made for, as part of the team's 44, before anyone else can mint.
///
///      Minting goes through OpenSea's SeaDrop (free mint; limits and timing are configured there).
///      Ownership, royalties and the transfer validator follow SeaDrop's own, audited code unchanged.
contract CrushedIt is ERC721SeaDrop {
    uint256 public constant SUPPLY = 888;
    uint256 public constant TEAM = 44;          // 40 random blocks for the team + the 4 gifts
    uint256 public constant GIFTS = 4;
    uint256 public constant FIRST_GIFT = 41;    // token ids 41..44 are the gifts
    uint256 public constant SHUFFLED = SUPPLY - GIFTS;

    /// The recipes pinned to tokens 41..44, in order: LOW RES, CCFF00, STOP THE PRESSES, CLAY DAY.
    uint16[GIFTS] public GIFT_RECIPES;

    /// keccak256(abi.encodePacked(secret)), fixed at deploy. The secret opens the reveal.
    bytes32 public immutable REVEAL_COMMIT;
    /// Merkle root over leaves keccak256(abi.encodePacked(recipeId, sha256(image), keccak256(metadataJson))).
    bytes32 public immutable IMAGE_ROOT;
    /// After this timestamp anyone can reveal even if the mint has not sold out.
    uint256 public immutable REVEAL_DEADLINE;

    bool public teamMinted;
    bool public revealed;
    uint256 public offset;

    /// Pre-reveal: every token shows this.
    string public sealedURI;
    bool public uriFrozen;

    struct Seal {
        address[] image;        // SSTORE2 chunks, in order
        address meta;           // SSTORE2 pointer to the metadata JSON (without the image field)
        bool done;
    }
    mapping(uint256 => Seal) private _seals;            // by recipe id
    mapping(uint256 => address[]) private _pending;     // chunks being uploaded, by recipe id

    event TeamMinted(address team, address[GIFTS] gifts);
    event Revealed(uint256 offset, bytes32 secret);
    event SealedURISet(string uri);
    event URIFrozen();
    event Sealed(uint256 indexed tokenId, uint256 indexed recipeId, uint256 bytesStored);
    event MetadataUpdate(uint256 _tokenId);     // ERC-4906 (the batch form comes from SeaDrop)

    error TeamAlreadyMinted();
    error TeamMustMintFirst();
    error AlreadyRevealed();
    error NotRevealed();
    error NotRevealable();
    error BadSecret();
    error Frozen();
    error ChunkTooBig();
    error NothingPending();
    error AlreadySealed();
    error BadProof();
    error NotToken();

    constructor(
        address[] memory allowedSeaDrop,
        bytes32 provenance,
        bytes32 revealCommit,
        bytes32 imageRoot,
        uint256 revealDeadline,
        uint16[GIFTS] memory giftRecipes,
        address royaltyReceiver
    ) ERC721SeaDrop("CRUSHED IT", "CRUSHEDIT", allowedSeaDrop) {
        _maxSupply = SUPPLY;
        _provenanceHash = provenance;
        _royaltyInfo = RoyaltyInfo(royaltyReceiver, 599);      // 5.99%
        REVEAL_COMMIT = revealCommit;
        IMAGE_ROOT = imageRoot;
        REVEAL_DEADLINE = revealDeadline;
        GIFT_RECIPES = giftRecipes;
    }

    // -- the team's 44 ------------------------------------------------------------------------------

    /// @notice Mint the team's 44 before anyone else: 40 to the team wallet, then the 4 gifts, so the gift
    ///         tokens are exactly ids 41..44. Can only happen once, and only while nothing has been minted.
    function mintTeam(address team, address[GIFTS] calldata gifts) external onlyOwner {
        if (teamMinted) revert TeamAlreadyMinted();
        if (_totalMinted() != 0) revert TeamMustMintFirst();
        teamMinted = true;
        _safeMint(team, TEAM - GIFTS);
        for (uint256 i = 0; i < GIFTS; ) {
            _mint(gifts[i], 1);
            unchecked { ++i; }
        }
        emit TeamMinted(team, gifts);
    }

    /// @dev SeaDrop mints are refused until the team's 44 are out, so the gift ids cannot move.
    function mintSeaDrop(address minter, uint256 quantity) external virtual override nonReentrant {
        _onlyAllowedSeaDrop(msg.sender);
        if (!teamMinted) revert TeamMustMintFirst();
        if (_totalMinted() + quantity > maxSupply()) {
            revert MintQuantityExceedsMaxSupply(_totalMinted() + quantity, maxSupply());
        }
        _safeMint(minter, quantity);
    }

    // -- reveal ----------------------------------------------------------------------------------------

    function revealable() public view returns (bool) {
        return _totalMinted() == SUPPLY || block.timestamp >= REVEAL_DEADLINE;
    }

    /// @notice Open the collection. Anyone can call it once the mint has sold out or the deadline has passed,
    ///         with the secret that was committed at deploy. The offset mixes that secret with the hash of
    ///         the previous block, so neither the deployer nor the caller can pick it.
    function reveal(bytes32 secret) external {
        if (revealed) revert AlreadyRevealed();
        if (!revealable()) revert NotRevealable();
        if (keccak256(abi.encodePacked(secret)) != REVEAL_COMMIT) revert BadSecret();
        revealed = true;
        offset = uint256(keccak256(abi.encodePacked(secret, blockhash(block.number - 1), _totalMinted()))) % SHUFFLED;
        emit Revealed(offset, secret);
        emit BatchMetadataUpdate(_startTokenId(), SUPPLY);
    }

    /// @notice Which recipe (1..888, the number in collection/manifest.json) a token shows.
    function recipeOf(uint256 tokenId) public view returns (uint256) {
        if (!_exists(tokenId)) revert NotToken();
        if (tokenId >= FIRST_GIFT && tokenId < FIRST_GIFT + GIFTS) {
            return GIFT_RECIPES[tokenId - FIRST_GIFT];
        }
        if (!revealed) revert NotRevealed();
        // rank of this token among the 884 shuffled ids, shifted, then mapped onto the 884 non-gift recipes
        uint256 rank = tokenId < FIRST_GIFT ? tokenId - 1 : tokenId - 1 - GIFTS;
        uint256 slot = (rank + offset) % SHUFFLED;
        return _nthFreeRecipe(slot);
    }

    /// @dev The n-th (0-based) recipe id in 1..888 that is not one of the gift recipes.
    function _nthFreeRecipe(uint256 n) internal view returns (uint256) {
        // sort the four gift recipes ascending (tiny, done every call rather than kept in storage)
        uint256[GIFTS] memory g;
        for (uint256 i = 0; i < GIFTS; ) {
            g[i] = GIFT_RECIPES[i];
            unchecked { ++i; }
        }
        for (uint256 i = 1; i < GIFTS; ) {
            uint256 v = g[i];
            uint256 j = i;
            while (j > 0 && g[j - 1] > v) { g[j] = g[j - 1]; unchecked { --j; } }
            g[j] = v;
            unchecked { ++i; }
        }
        uint256 r = n + 1;
        for (uint256 i = 0; i < GIFTS; ) {
            if (g[i] <= r) r += 1;
            unchecked { ++i; }
        }
        return r;
    }

    // -- URIs ------------------------------------------------------------------------------------------

    function setSealedURI(string calldata uri) external onlyOwner {
        if (uriFrozen) revert Frozen();
        sealedURI = uri;
        emit SealedURISet(uri);
    }

    /// @notice Lock the pre-reveal URI. (The base URI is SeaDrop's own and stays owner-settable, as on every
    ///         SeaDrop collection; what makes a block permanent is sealing it on-chain, below.)
    function freezeURI() external onlyOwner {
        uriFrozen = true;
        emit URIFrozen();
    }

    function tokenURI(uint256 tokenId) public view virtual override returns (string memory) {
        if (!_exists(tokenId)) revert URIQueryForNonexistentToken();
        bool gift = tokenId >= FIRST_GIFT && tokenId < FIRST_GIFT + GIFTS;
        if (!revealed && !gift) return sealedURI;
        uint256 recipe = recipeOf(tokenId);
        Seal storage s = _seals[recipe];
        if (s.done) return _onChainURI(s);
        return string(abi.encodePacked(_baseURI(), _toString(recipe)));
    }

    function _onChainURI(Seal storage s) internal view returns (string memory) {
        bytes memory meta = SSTORE2.read(s.meta);       // '{"name":...,"attributes":[...]' with no closing brace
        bytes memory img = _readChunks(s.image);
        return string(abi.encodePacked(
            "data:application/json;base64,",
            _base64(abi.encodePacked(meta, ',"image":"data:image/jpeg;base64,', _base64(img), '"}'))
        ));
    }

    // -- sealing: the holder (or anyone) pays to put the full image and metadata on-chain ------------

    uint256 public constant CHUNK = 24_000;

    /// @notice Upload one chunk of the JPEG for a token's recipe. Chunks go in order; index 0 restarts.
    function sealChunk(uint256 tokenId, uint256 index, bytes calldata data) external {
        uint256 recipe = recipeOf(tokenId);
        if (_seals[recipe].done) revert AlreadySealed();
        if (data.length == 0 || data.length > CHUNK) revert ChunkTooBig();
        address[] storage p = _pending[recipe];
        if (index == 0) delete _pending[recipe];
        if (index != p.length) revert NothingPending();
        p.push(SSTORE2.write(data));
    }

    /// @notice Finish the seal: the metadata JSON (without its closing brace and without an image field)
    ///         plus a Merkle proof that (recipe, sha256(image), keccak256(meta)) is in IMAGE_ROOT.
    function sealFinish(uint256 tokenId, bytes calldata meta, bytes32[] calldata proof) external {
        uint256 recipe = recipeOf(tokenId);
        Seal storage s = _seals[recipe];
        if (s.done) revert AlreadySealed();
        address[] storage p = _pending[recipe];
        if (p.length == 0) revert NothingPending();
        bytes memory img = _readChunks(p);
        bytes32 leaf = keccak256(abi.encodePacked(uint256(recipe), sha256(img), keccak256(meta)));
        if (!_verify(proof, IMAGE_ROOT, leaf)) revert BadProof();
        s.image = p;
        s.meta = SSTORE2.write(meta);
        s.done = true;
        delete _pending[recipe];
        emit Sealed(tokenId, recipe, img.length + meta.length);
        emit MetadataUpdate(tokenId);
    }

    function isSealed(uint256 tokenId) external view returns (bool) {
        return _seals[recipeOf(tokenId)].done;
    }

    /// @notice The stored JPEG bytes of a sealed token (empty if not sealed).
    function sealedImage(uint256 tokenId) external view returns (bytes memory) {
        Seal storage s = _seals[recipeOf(tokenId)];
        if (!s.done) return "";
        return _readChunks(s.image);
    }

    function _readChunks(address[] storage ptrs) internal view returns (bytes memory out) {
        uint256 n = ptrs.length;
        for (uint256 i = 0; i < n; ) {
            out = abi.encodePacked(out, SSTORE2.read(ptrs[i]));
            unchecked { ++i; }
        }
    }

    function _verify(bytes32[] calldata proof, bytes32 root, bytes32 leaf) internal pure returns (bool) {
        bytes32 h = leaf;
        for (uint256 i = 0; i < proof.length; ) {
            bytes32 p = proof[i];
            h = h < p ? keccak256(abi.encodePacked(h, p)) : keccak256(abi.encodePacked(p, h));
            unchecked { ++i; }
        }
        return h == root;
    }

    // -- base64 (OpenZeppelin's, inlined so the SeaDrop tree stays untouched) -------------------------

    function _base64(bytes memory data) internal pure returns (string memory) {
        if (data.length == 0) return "";
        string memory table = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        string memory result = new string(4 * ((data.length + 2) / 3));
        assembly {
            let tablePtr := add(table, 1)
            let resultPtr := add(result, 32)
            for { let i := 0 } lt(i, mload(data)) { } {
                i := add(i, 3)
                let input := and(mload(add(data, i)), 0xffffff)
                mstore8(resultPtr, mload(add(tablePtr, and(shr(18, input), 0x3F))))
                resultPtr := add(resultPtr, 1)
                mstore8(resultPtr, mload(add(tablePtr, and(shr(12, input), 0x3F))))
                resultPtr := add(resultPtr, 1)
                mstore8(resultPtr, mload(add(tablePtr, and(shr(6, input), 0x3F))))
                resultPtr := add(resultPtr, 1)
                mstore8(resultPtr, mload(add(tablePtr, and(input, 0x3F))))
                resultPtr := add(resultPtr, 1)
            }
            switch mod(mload(data), 3)
            case 1 { mstore8(sub(resultPtr, 1), 0x3d) mstore8(sub(resultPtr, 2), 0x3d) }
            case 2 { mstore8(sub(resultPtr, 1), 0x3d) }
        }
        return result;
    }

    function supportsInterface(bytes4 interfaceId) public view virtual override returns (bool) {
        return interfaceId == 0x49064906 || super.supportsInterface(interfaceId);   // ERC-4906
    }
}
