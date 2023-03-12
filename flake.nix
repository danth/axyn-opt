{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixpkgs-unstable";
    utils.url = "github:numtide/flake-utils";
  };

  outputs =
    { nixpkgs, utils, self, ... }:
    {
      nixosModules.axyn = import ./nixos.nix self;
    } //
    (utils.lib.eachDefaultSystem (
      system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        nltkData = pkgs.runCommandLocal "nltk-data" {
          punkt = pkgs.fetchzip {
            name = "punkt";
            url = "https://raw.githubusercontent.com/nltk/nltk_data/gh-pages/packages/tokenizers/punkt.zip";
            sha256 = "SKZu26K17qMUg7iCFZey0GTECUZ+sTTrF/pqeEgJCos=";
          };
        } ''
          mkdir -p $out/tokenizers
          ln -s $punkt $out/tokenizers/punkt
        '';

      in {
        packages.default = pkgs.python3Packages.buildPythonApplication {
          name = "axyn";
          src = ./.;

          postPatch = ''
            substituteInPlace axyn/generator.py \
              --replace gpt2-large ${pkgs.callPackage ./model.nix {}}
          '';

          nativeBuildInputs = [ pkgs.makeWrapper ];
          postFixup = ''
            wrapProgram $out/bin/axyn --set NLTK_DATA ${nltkData}
          '';

          propagatedBuildInputs =
            with pkgs.python3Packages;
            [ discordpy nltk torch transformers ];
        };
      }
    ));
}
