// SPDX-License-Identifier: MIT
pragma solidity 0.8.28;

import {ERC721} from "@openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC2981} from "@openzeppelin/contracts/token/common/ERC2981.sol";
import {Ownable} from "@openzeppelin/contracts/access/Ownable.sol";
import {Strings} from "@openzeppelin/contracts/utils/Strings.sol";

/// @title CRUSHED
/// @notice 888 perfect cubes of crushed nostalgic shit.
/// @dev Every block is generated from a fixed recipe (see blender/). The sha256 of the
///      full manifest is fixed at deploy, so the traits and the one-of-ones can't move.
///      Which token gets which recipe is decided by a commit-reveal offset after mint,
///      so nobody (including the deployer) can aim a mint at a one-of-one.
contract Crushed is ERC721, ERC2981, Ownable {
    using Strings for uint256;

    uint256 public constant MAX_SUPPLY = 888;

    /// sha256(collection/manifest.json)
    bytes32 public immutable PROVENANCE;
    /// keccak256(abi.encodePacked(secret)), committed before mint
    bytes32 public immutable REVEAL_COMMIT;

    uint256 public totalMinted;
    uint256 public price;
    uint256 public maxPerWallet;
    bool public mintOpen;

    bool public revealed;
    uint256 public offset;

    bool public metadataFrozen;
    string private _base;
    string private _sealedURI;
    string private _contractURI;

    mapping(address => uint256) public mintedBy;

    event MintOpen(bool open);
    event Revealed(uint256 offset);
    event MetadataFrozen();
    // ERC-4906: lets marketplaces refresh when a block changes (reveal, re-render, whatever comes later)
    event MetadataUpdate(uint256 _tokenId);
    event BatchMetadataUpdate(uint256 _fromTokenId, uint256 _toTokenId);

    error MintClosed();
    error SoldOut();
    error WalletLimit();
    error WrongPrice();
    error BadQuantity();
    error AlreadyRevealed();
    error NotRevealable();
    error BadSecret();
    error Frozen();
    error WithdrawFailed();

    constructor(
        address owner_,
        bytes32 provenance,
        bytes32 revealCommit,
        uint256 price_,
        uint256 maxPerWallet_,
        string memory sealedURI_,
        string memory contractURI_,
        address royaltyReceiver,
        uint96 royaltyBps
    ) ERC721("CRUSHED", "CRUSHED") Ownable(owner_) {
        PROVENANCE = provenance;
        REVEAL_COMMIT = revealCommit;
        price = price_;
        maxPerWallet = maxPerWallet_;
        _sealedURI = sealedURI_;
        _contractURI = contractURI_;
        _setDefaultRoyalty(royaltyReceiver, royaltyBps);
    }

    // ---------------------------------------------------------------- mint

    function mint(uint256 quantity) external payable {
        if (!mintOpen) revert MintClosed();
        if (quantity == 0) revert BadQuantity();
        if (msg.value != price * quantity) revert WrongPrice();
        if (mintedBy[msg.sender] + quantity > maxPerWallet) revert WalletLimit();
        mintedBy[msg.sender] += quantity;
        _mintMany(msg.sender, quantity);
    }

    /// @notice Team, collaborators and giveaways. Same supply cap, same randomness.
    function ownerMint(address to, uint256 quantity) external onlyOwner {
        if (quantity == 0) revert BadQuantity();
        _mintMany(to, quantity);
    }

    function _mintMany(address to, uint256 quantity) internal {
        uint256 start = totalMinted;
        if (start + quantity > MAX_SUPPLY) revert SoldOut();
        totalMinted = start + quantity;
        for (uint256 i = 1; i <= quantity; ++i) {
            _mint(to, start + i);
        }
    }

    // ---------------------------------------------------------------- reveal

    /// @notice Publish the secret committed at deploy. The offset mixes it with a recent
    ///         block hash, so the owner can't choose it and minters couldn't predict it.
    function reveal(bytes32 secret) external onlyOwner {
        if (revealed) revert AlreadyRevealed();
        if (mintOpen) revert NotRevealable();
        if (keccak256(abi.encodePacked(secret)) != REVEAL_COMMIT) revert BadSecret();
        uint256 r = uint256(keccak256(abi.encodePacked(secret, blockhash(block.number - 1), totalMinted)));
        offset = r % MAX_SUPPLY;
        revealed = true;
        emit Revealed(offset);
        emit BatchMetadataUpdate(1, MAX_SUPPLY);
    }

    /// @notice Which manifest recipe a token is. Anyone can check this against manifest.json.
    function recipeOf(uint256 tokenId) public view returns (uint256) {
        _requireOwned(tokenId);
        return ((tokenId - 1 + offset) % MAX_SUPPLY) + 1;
    }

    // ---------------------------------------------------------------- metadata

    function tokenURI(uint256 tokenId) public view override returns (string memory) {
        _requireOwned(tokenId);
        if (!revealed || bytes(_base).length == 0) return _sealedURI;
        return string.concat(_base, tokenId.toString());
    }

    function contractURI() external view returns (string memory) {
        return _contractURI;
    }

    function setBaseURI(string calldata base) external onlyOwner {
        if (metadataFrozen) revert Frozen();
        _base = base;
        emit BatchMetadataUpdate(1, MAX_SUPPLY);
    }

    function setSealedURI(string calldata uri) external onlyOwner {
        if (metadataFrozen) revert Frozen();
        _sealedURI = uri;
        emit BatchMetadataUpdate(1, MAX_SUPPLY);
    }

    function setContractURI(string calldata uri) external onlyOwner {
        _contractURI = uri;
    }

    /// @notice One-way. After this the images and traits are what they are.
    function freezeMetadata() external onlyOwner {
        metadataFrozen = true;
        emit MetadataFrozen();
    }

    // ---------------------------------------------------------------- admin

    function setMintOpen(bool open) external onlyOwner {
        if (open && revealed) revert AlreadyRevealed();
        mintOpen = open;
        emit MintOpen(open);
    }

    function setPrice(uint256 price_) external onlyOwner {
        price = price_;
    }

    function setMaxPerWallet(uint256 max_) external onlyOwner {
        maxPerWallet = max_;
    }

    function setRoyalty(address receiver, uint96 bps) external onlyOwner {
        _setDefaultRoyalty(receiver, bps);
    }

    function withdraw(address payable to) external onlyOwner {
        (bool ok,) = to.call{value: address(this).balance}("");
        if (!ok) revert WithdrawFailed();
    }

    function supportsInterface(bytes4 interfaceId) public view override(ERC721, ERC2981) returns (bool) {
        return interfaceId == bytes4(0x49064906) || super.supportsInterface(interfaceId);
    }
}
