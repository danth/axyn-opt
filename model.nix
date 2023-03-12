{ fetchurl, linkFarmFromDrvs }:
let version = "212095d5832abbf9926672e1c1e8d14312a3be20";
in linkFarmFromDrvs "gpt2-large" [
  (fetchurl {
    url = "https://huggingface.co/gpt2-large/resolve/${version}/merges.txt";
    sha256 = "HOFmR3PFDz4MyIQmGak+3EYkUltyixiKngvjO3cmrcU=";
  })
  (fetchurl {
    url = "https://huggingface.co/gpt2-large/resolve/${version}/config.json";
    sha256 = "f8zc/WYiBVNCpzTGY+4LYf9P1pf0JGdZXfC/REjIwXA=";
  })
  (fetchurl {
    url = "https://huggingface.co/gpt2-large/resolve/${version}/pytorch_model.bin";
    sha256 = "8d3ade6b55ac440e926112267b9ec784097437c7300544b8beec562a411428ec";
  })
  (fetchurl {
    url = "https://huggingface.co/gpt2-large/resolve/${version}/vocab.json";
    sha256 = "GWE5ZovmPztdZXRCcxeugvYSqXxdHNrzbtIlbb9jZ4M=";
  })
]
