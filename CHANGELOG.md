# CHANGELOG



## v1.10.2 (2024-06-07)

###  

* Pin `pypa/gh-action-pypi-publish` GHA to `v1.8.11` ([`b824e18`](https://github.com/WIPACrepo/wipac-dev-tools/commit/b824e18b7ac819f2bea02a28e6bb8bae1e18ed97))


## v1.10.1 (2024-06-07)

###  

* Lower `python-semantic-release` GHAs to `v8.7.0` (#98)

* Lower `python-semantic-release` GHAs to `v8.7.0`

* &lt;bot&gt; update dependencies*.log files(s)

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`d4a076b`](https://github.com/WIPACrepo/wipac-dev-tools/commit/d4a076b329726004cf855185112de2f870b6b537))


## v1.10.0 (2024-05-31)

###  

* Use `WIPACrepo/wipac-dev-py-setup-action@v4` Followup (#96)

* use `WIPACrepo/wipac-dev-py-setup-action@toml-pkg-version-fix`

* remove version

* move version to toml

* re-add `__version__`, now with `importlib.metadata.version`

* req `importlib-metadata`

* &lt;bot&gt; update pyproject.toml

* it&#39;s `importlib_metadata`

* test update

* use `WIPACrepo/wipac-dev-py
-dependencies-action@main`

* &lt;bot&gt; update dependencies*.log files(s)

* use `WIPACrepo/wipac-dev-py-dependencies-action@v1.3`

* use `WIPACrepo/wipac-dev-py-setup-action@v4.0`

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`1663c76`](https://github.com/WIPACrepo/wipac-dev-tools/commit/1663c766cd9d0ccd95b104a070de786335649ccc))

* Use `WIPACrepo/wipac-dev-py-dependencies-action` and Update &#34;Release&#34; CI (#90)

* try `WIPACrepo/wipac-dev-py-dependencies-action@first`

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* &lt;bot&gt; update dependencies*.log files(s)

* try `WIPACrepo/wipac-dev-py-setup-action@pre-3.0`

* &lt;bot&gt; update dependencies*.log files(s)

* use `WIPACrepo/wipac-dev-py-setup-action@v3.0`

* use `WIPACrepo/wipac-dev-py-dependencies-action@v1.0`

* &lt;bot&gt; update dependencies*.log files(s)

* try `WIPACrepo/wipac-dev-py-versions-action@with-semvar`

* with `WIPACrepo/wipac-dev-py-versions-action@v2.2`

* try `WIPACrepo/wipac-dev-py-dependencies-action@use-dev-tools`

* use `WIPACrepo/wipac-dev-py-dependencies-action@v1.1`

* try `WIPACrepo/wipac-dev-py-setup-action@use-devtools`

* use `WIPACrepo/wipac-dev-py-setup-action@v3.1`

* &lt;bot&gt; update dependencies*.log files(s)

* split `release` into more steps: python sr, pypi, github

* &lt;bot&gt; update dependencies*.log files(s)

* remove unneeded `name`s

* clean up `if`s

* call it `writable-branch-detect`

* typo

* add echo

* put in bash

* `OKAY`

* misc

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`7bb3d18`](https://github.com/WIPACrepo/wipac-dev-tools/commit/7bb3d1837f679846fc45973303cce68d0658897b))

### [minor]

* Use `WIPACrepo/wipac-dev-py-setup-action@v4` [minor] (#94)

* try `WIPACrepo/wipac-dev-py-setup-action@toml`

* &lt;bot&gt; update dependencies*.log files(s)

* trigger re-run

* &lt;bot&gt; update dependencies*.log files(s)

* rm setup.cfg

* set `python_min`

* add keywords

* &lt;bot&gt; update pyproject.toml

* &lt;bot&gt; update README.md

* migrate setup.cfg&#39;s metadata to gha `with`

* &lt;bot&gt; update pyproject.toml

* &lt;bot&gt; update README.md

* use `WIPACrepo/wipac-dev-py-versions-action@pyproject.toml`

* use `WIPACrepo/wipac-dev-py-versions-action@v2.3`

* use `WIPACrepo/wipac-dev-py-dependencies-action@pyproject.toml`

* &lt;bot&gt; update pyproject.toml

* use `WIPACrepo/wipac-dev-py-dependencies-action@v1.2`

* &lt;bot&gt; update pyproject.toml

* clear toml

* &lt;bot&gt; update pyproject.toml

* &lt;bot&gt; update dependencies*.log files(s)

* add optional deps

* remove `[tool.setuptools.package-data]`

* &lt;bot&gt; update pyproject.toml

* &lt;bot&gt; update dependencies*.log files(s)

* use `WIPACrepo/wipac-dev-py-setup-action@v4.0`

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`caecc65`](https://github.com/WIPACrepo/wipac-dev-tools/commit/caecc655152108ed6e68e1c56a4fc0182a5b2fe6))


## v1.9.1 (2024-02-08)

###  

* Correct Naming: `semver_parser_tools.py` (#92)

* Correct Naming: `semver_parser_tools.py`

* mv semvar_parser_tools.py

* &lt;bot&gt; update dependencies*.log files(s)

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`445da2e`](https://github.com/WIPACrepo/wipac-dev-tools/commit/445da2eaed1fda5d24eac91130b359718e92d6fa))


## v1.9.0 (2024-02-02)

### [minor]

* Add `semvar_parser_tools.py` [minor] (#91)

* Add `semvar_parser_tools.py`

* &lt;bot&gt; update setup.cfg

* &lt;bot&gt; update dependencies*.log files(s)

* fix import

* generalize to `list_all_majmin_versions()`

* misc

* &lt;bot&gt; update setup.cfg

* &lt;bot&gt; update dependencies*.log files(s)

* fix ci

* typo

* type fix

* don&#39;t explicitly export

---------

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`0184a71`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0184a71ca8fc01ed25f539ae909d9804a28f5315))


## v1.8.2 (2023-11-30)

###  

* Add `specialty_loggers` to `set_level()` (#89)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`95fa8ba`](https://github.com/WIPACrepo/wipac-dev-tools/commit/95fa8bad27361596f0ac73cb7b46beb81ecc0b83))


## v1.8.1 (2023-11-22)

###  

* Make `sensitive_data_tools.is_name_sensitive()` (#88) ([`dabea36`](https://github.com/WIPACrepo/wipac-dev-tools/commit/dabea36e80e74c10e461b64106375beb0aa264af))


## v1.8.0 (2023-11-22)

### [minor]

* Make `sensitive_data_tools.obfuscate_value_if_sensitive()` [minor] (#87)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`85ccbb3`](https://github.com/WIPACrepo/wipac-dev-tools/commit/85ccbb3ae74d9700bda9c2d565a55ae986bcb0ee))


## v1.7.1 (2023-10-25)

###  

* Bump `WIPACrepo/wipac-dev-py-setup-action` (#86)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`f5d8f1f`](https://github.com/WIPACrepo/wipac-dev-tools/commit/f5d8f1fd2db73d5a2134c04312e52a84fe1c88e2))


## v1.7.0 (2023-10-03)

###  

* Python 3.12 and Use `WIPACrepo/wipac-dev-py-setup-action@v2.6` (#84)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`7093abb`](https://github.com/WIPACrepo/wipac-dev-tools/commit/7093abb17eafadff9f75b0ff55efb7d5e348818f))

### [minor]

* Python 3.12 and GHA Followup [minor] (#85) ([`26f6fe3`](https://github.com/WIPACrepo/wipac-dev-tools/commit/26f6fe3396b1d843c4f738d80ff18c462da405b3))


## v1.6.16 (2023-05-24)

###  

* bump pv-versions action to v2.1 ([`13c4690`](https://github.com/WIPACrepo/wipac-dev-tools/commit/13c4690599e971d1aa26fb6e30c9b67799d4c850))


## v1.6.15 (2023-04-05)

###  

* Fix WIPAC GHA Package Versions (#77) ([`06cd213`](https://github.com/WIPACrepo/wipac-dev-tools/commit/06cd21375fccc8407d5d0e9c709d1feb69b16982))


## v1.6.14 (2023-04-03)

###  

* Update wipac-cicd.yml (#76)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`dc2e61a`](https://github.com/WIPACrepo/wipac-dev-tools/commit/dc2e61a6b4b189b22242d52a757a93bec3940c00))


## v1.6.13 (2023-03-09)

###  

* Obfuscate Sensitive Env Vars (#70)

Co-authored-by: David Schultz &lt;davids24@gmail.com&gt;
Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`a13b989`](https://github.com/WIPACrepo/wipac-dev-tools/commit/a13b989d340c492755a89a3bbe7376c47637ac96))


## v1.6.12 (2023-02-17)

###  

* dependabot: bump WIPACrepo/wipac-dev-py-setup-action from 1.9 to 1.11 (#67)

Co-authored-by: dependabot[bot] &lt;49699333+dependabot[bot]@users.noreply.github.com&gt; ([`3e6ced8`](https://github.com/WIPACrepo/wipac-dev-tools/commit/3e6ced8bd1bb33986923ece2879d745ad2d11dcf))


## v1.6.11 (2023-02-17)

###  

* CI Updates (#68)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`1d0e574`](https://github.com/WIPACrepo/wipac-dev-tools/commit/1d0e5742d1188d1b8a31b5dafe80193f9a9f0d51))

* dependabot: bump certifi from 2022.9.24 to 2022.12.7 (#63)

Bumps [certifi](https://github.com/certifi/python-certifi) from 2022.9.24 to 2022.12.7.
- [Release notes](https://github.com/certifi/python-certifi/releases)
- [Commits](https://github.com/certifi/python-certifi/compare/2022.09.24...2022.12.07)

---
updated-dependencies:
- dependency-name: certifi
  dependency-type: direct:production
...

Signed-off-by: dependabot[bot] &lt;support@github.com&gt;

Signed-off-by: dependabot[bot] &lt;support@github.com&gt;
Co-authored-by: dependabot[bot] &lt;49699333+dependabot[bot]@users.noreply.github.com&gt; ([`4ebfdd9`](https://github.com/WIPACrepo/wipac-dev-tools/commit/4ebfdd9a53e909ee281accd089c3323636026000))


## v1.6.10 (2022-11-17)

###  

* Use `WIPACrepo/wipac-dev-project-action@v1` (#60)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`83888c1`](https://github.com/WIPACrepo/wipac-dev-tools/commit/83888c1600188e2cee70a5a95e5a1a6c7462a370))


## v1.6.9 (2022-11-14)

###  

* dependabot: bump WIPACrepo/wipac-dev-py-setup-action from 1.8 to 1.9 (#57)

Co-authored-by: dependabot[bot] &lt;49699333+dependabot[bot]@users.noreply.github.com&gt; ([`d44759e`](https://github.com/WIPACrepo/wipac-dev-tools/commit/d44759e1dd02b02f9d9d8d84ec64b916b09d77df))


## v1.6.8 (2022-11-14)

###  

* Auto-Add `dependencies` PRs/Issues to Project (#59)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`32ee103`](https://github.com/WIPACrepo/wipac-dev-tools/commit/32ee1037bdfafc20707971cf240bbf8513e80a1a))


## v1.6.7 (2022-11-04)

###  

* Update GHA Conditional Logic Further (#56) ([`5e913d9`](https://github.com/WIPACrepo/wipac-dev-tools/commit/5e913d9964d42c83aa943d3f2ed4afd46d1b199b))


## v1.6.6 (2022-11-04)

###  

* Update GHA Conditional Logic (#55) ([`c945b67`](https://github.com/WIPACrepo/wipac-dev-tools/commit/c945b6731b6b527bb1874af2ebf2fae3a017c865))


## v1.6.5 (2022-11-04)

###  

* dependabot: bump actions/setup-python from 2 to 4 (#51)

Co-authored-by: dependabot[bot] &lt;49699333+dependabot[bot]@users.noreply.github.com&gt; ([`4522808`](https://github.com/WIPACrepo/wipac-dev-tools/commit/452280874574387463a7c0971c512f349df030f4))


## v1.6.4 (2022-11-04)

###  

* Fix Dependabot Aborted CI (#54) ([`2ac711f`](https://github.com/WIPACrepo/wipac-dev-tools/commit/2ac711f49e15399551b8af647ba93fd3d364d1d1))


## v1.6.3 (2022-11-04)

###  

* Tweak Dependabot Settings (#53)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`f02db6e`](https://github.com/WIPACrepo/wipac-dev-tools/commit/f02db6e7cbcd65ae4cbea380b481c78e667bb371))


## v1.6.2 (2022-11-04)

###  

* Update `dependabot.yml` (#50) ([`c2e4fd5`](https://github.com/WIPACrepo/wipac-dev-tools/commit/c2e4fd58290fe422d16a686f5eda4d91a2d40b26))


## v1.6.1 (2022-11-04)

###  

* Create `dependabot.yml` (#49) ([`d6c07e5`](https://github.com/WIPACrepo/wipac-dev-tools/commit/d6c07e5938840bca5cac1c1a863bd5d281941ada))


## v1.6.0 (2022-10-25)

### [minor]

* Python 3.11 [minor] (#48)

Co-authored-by: github-actions &lt;github-actions@github.com&gt;
Co-authored-by: Ric Evans &lt;19216225+ric-evans@users.noreply.github.com&gt; ([`6aec2a3`](https://github.com/WIPACrepo/wipac-dev-tools/commit/6aec2a30470c8a6bfd335941f05d08d6f2096610))


## v1.5.6 (2022-10-06)

###  

* Logger Hierarchies Fix (#47) ([`818f189`](https://github.com/WIPACrepo/wipac-dev-tools/commit/818f189a0bd5127156f4edc7abd129ae52315f0b))


## v1.5.5 (2022-10-05)

###  

* Follow-up to &#34;Logger Hierarchies Updated&#34; (#46) ([`01a406b`](https://github.com/WIPACrepo/wipac-dev-tools/commit/01a406b04c1b960493e10ec4c42280a5b83b30e2))


## v1.5.4 (2022-10-05)

###  

* Logger Hierarchies Updated (#45) ([`762bcd0`](https://github.com/WIPACrepo/wipac-dev-tools/commit/762bcd0f1555d190a3f00e24d026a25374b010bd))


## v1.5.3 (2022-10-04)

###  

* More Logging Enhancements (#44) ([`7c9dab3`](https://github.com/WIPACrepo/wipac-dev-tools/commit/7c9dab35d0bd2b5c2461de0875fb4a119e999e69))


## v1.5.2 (2022-10-04)

###  

* Logging Enhancements and Tests (#36)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`910b407`](https://github.com/WIPACrepo/wipac-dev-tools/commit/910b40751d08bba8e1504d491879642480433446))


## v1.5.1 (2022-09-26)

###  

* `argparse_tools`: Auto-wrap `ArgumentTypeError` If Needed (#43)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`0d2c36d`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0d2c36d888705a4898d9aeaece159e51b0dc7582))


## v1.5.0 (2022-09-15)

### [minor]

* Argparse Tools [minor] (#42)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`b5f78cf`](https://github.com/WIPACrepo/wipac-dev-tools/commit/b5f78cf4bd715968a1370aed150a71c7be29df12))


## v1.4.0 (2022-08-26)

### [minor]

* Add `wipac_dev_tools.strtobool()` [minor] (#40)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`4fcde91`](https://github.com/WIPACrepo/wipac-dev-tools/commit/4fcde91bd2905858d98a97ee4cc90eccb1e18029))


## v1.3.1 (2022-07-18)

###  

* Update README (#38)

* add doc for `wipac_dev_tools.from_environment_as_dataclass()`

* add `_Available for Python 3.6+_` for other tools ([`20c5cbb`](https://github.com/WIPACrepo/wipac-dev-tools/commit/20c5cbb457e044296916e0d64c0a6a044550ecd1))


## v1.3.0 (2022-07-18)

### [minor]

* Add `from_environment_as_dataclass()` [minor] (#37)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`45e75dc`](https://github.com/WIPACrepo/wipac-dev-tools/commit/45e75dcc8e3d9e9638bca045e6f9f52db9c27f87))


## v1.2.2 (2022-05-31)

###  

* Add Signatures and Docblocks to README (#35)

* add the doc blocks (verbatim) to readme (could be automated someday...)

* fix heading ([`0d87f1c`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0d87f1c927f58acd2107506c549c8a5b2f7bb07a))


## v1.2.1 (2022-05-31)

###  

* Bump `wipac-dev-py-setup-action` &amp; `wipac-dev-py-versions-action` (#34)

* use `WIPACrepo/wipac-dev-py-setup-action@constants`

* add inputs

* &lt;bot&gt; update setup.cfg

* &lt;bot&gt; update requirements.txt

* (temp)

* Revert &#34;(temp)&#34;

This reverts commit fe60dc3aeb5919dd1d99cea6555b1c6e0dd3a298.

* (temp)

* Revert &#34;(temp)&#34;

This reverts commit 11ab8db96b4acf734e8ccd5ed092723a8d5442b5.

* Revert &#34;Revert &#34;(temp)&#34;&#34;

This reverts commit 0862d8f6e279c9cdb34fc3c2501dce17c2ff9f99.

* Revert &#34;Revert &#34;Revert &#34;(temp)&#34;&#34;&#34;

This reverts commit 7421edab25b256d5c8cf8de92a9d36148cdb63f8.

* move `author` and `author_email` to config

* bump py-versions to `readme-updates`

* `WIPACrepo/wipac-dev-py-setup-action@v1.6`

* &lt;bot&gt; update setup.cfg

* `WIPACrepo/wipac-dev-py-versions-action@v1.1`

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`34ddf4b`](https://github.com/WIPACrepo/wipac-dev-tools/commit/34ddf4b0b503a1771cc58a2df61ec91856531487))


## v1.2.0 (2022-05-16)

### [minor]

* Logging Tools: Production Ready [minor] (#33)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`8cad3eb`](https://github.com/WIPACrepo/wipac-dev-tools/commit/8cad3eb24f765ab11c02b2f9f27d4db000731ade))


## v1.1.6 (2022-05-16)

###  

* A Couple Logging Tools (#32) ([`0352b09`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0352b09fe847466b4b486de7e3912303c393da6d))


## v1.1.5 (2022-04-11)

###  

* Bump `WIPACrepo/wipac-dev-py-setup-action` (#30)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`6f07357`](https://github.com/WIPACrepo/wipac-dev-tools/commit/6f07357c57a796a8a8b4bd63fee615741bad48a2))


## v1.1.4 (2022-03-18)

###  

* Use WIPAC GH Action Packages (#29)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`8c865a8`](https://github.com/WIPACrepo/wipac-dev-tools/commit/8c865a87af582441c5c235a2e4149b81b540a6af))


## v1.1.3 (2022-03-15)

###  

* Add Backup MyPy Script (#27) ([`7adb700`](https://github.com/WIPACrepo/wipac-dev-tools/commit/7adb700daadc38ae16aa5132bdae2605101408c7))


## v1.1.2 (2022-03-11)

###  

* Python Version Testing Patch (#26) ([`45bee10`](https://github.com/WIPACrepo/wipac-dev-tools/commit/45bee10e166b2edaad5b9963e244162d70a86b36))


## v1.1.1 (2022-03-08)

###  

* PyPI Follow-Up (#25)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`944e94e`](https://github.com/WIPACrepo/wipac-dev-tools/commit/944e94e61c0719f5aad8c8e2bd91e5d6e4243fa2))


## v1.1.0 (2022-03-07)

### [minor]

* PyPI Readiness [minor] (#22)

Co-authored-by: github-actions &lt;github-actions@github.com&gt; ([`af42b27`](https://github.com/WIPACrepo/wipac-dev-tools/commit/af42b273b97c774e21abd0b6dbedd74e2aaae8e5))


## v1.0.14 (2022-02-04)

###  

* MyPy Support for Multiple Requirements Files (#19) ([`b637fbe`](https://github.com/WIPACrepo/wipac-dev-tools/commit/b637fbeeea6e6fca256e043bd440c245a2a5b556))


## v1.0.13 (2022-01-18)

###  

* GitHub Linter Actions: flake8 and mypy (#18) ([`d37a1f8`](https://github.com/WIPACrepo/wipac-dev-tools/commit/d37a1f8689fdcbe0ac808d362ccf6e09d1806319))


## v1.0.12 (2021-10-07)

###  

* Merge pull request #7 from WIPACrepo/python-themed-make-script

Adds some build and test infrastructure ([`d80538e`](https://github.com/WIPACrepo/wipac-dev-tools/commit/d80538ec393f3f5d1081f17aeeff1423919f120d))

* There are no requirements, only requirements-dev ([`50bbfac`](https://github.com/WIPACrepo/wipac-dev-tools/commit/50bbfaccc1d8a40bbfb5323324b062f83b909e18))

* Bump requirements to satisfy check ([`010e560`](https://github.com/WIPACrepo/wipac-dev-tools/commit/010e560cc94e82b7091a0d01675a83775b59f692))

* KISS in GitHub Actions ([`25a1145`](https://github.com/WIPACrepo/wipac-dev-tools/commit/25a11450aa2134449aeb0f771902403d1cac5dd7))

* Use the correct argument for the requirements file ([`c01544b`](https://github.com/WIPACrepo/wipac-dev-tools/commit/c01544b6dbdec6e08c391935930facf7af298323))

* Rename and check if the GitHub Action works correctly ([`20b750b`](https://github.com/WIPACrepo/wipac-dev-tools/commit/20b750b6bb35a805a44a28074c97eeb263d76e50))

* Now with Check Requirements ([`1ab13ea`](https://github.com/WIPACrepo/wipac-dev-tools/commit/1ab13ea422c665b12d5cc02b788ae29051d4333d))


## v1.0.11 (2021-08-23)

###  

* Allow Pinned Versions for Dependencies (#17) ([`84d477b`](https://github.com/WIPACrepo/wipac-dev-tools/commit/84d477b551078f7c3b3411ab21d1026bcfd6c8fb))


## v1.0.10 (2021-05-27)

###  

* `SetupShop`: Add Support for README.rst (#13) ([`0833f00`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0833f00a4cd5919152678bb90307db31bed014af))


## v1.0.9 (2021-05-27)

###  

* Try Setup Install (GH Action) Update (#12) ([`93d9488`](https://github.com/WIPACrepo/wipac-dev-tools/commit/93d94885b81061f6617a2c8647a9d4d518c31a48))


## v1.0.8 (2021-05-27)

###  

* python-versions matrix bug-fix: need quotes (otherwise 3.10 goes to 3.1) ([`c2c6f93`](https://github.com/WIPACrepo/wipac-dev-tools/commit/c2c6f938aebc097ee2ae300445fe6d6a94bd9391))


## v1.0.7 (2021-05-26)

###  

* GH Action Setup Install with All Supported Python Versions (#11) ([`1d98a79`](https://github.com/WIPACrepo/wipac-dev-tools/commit/1d98a797a01f47e31ebe2ad2992af9878e5a10c1))


## v1.0.6 (2021-05-24)

###  

* Python Setup Additions (#10) ([`001b569`](https://github.com/WIPACrepo/wipac-dev-tools/commit/001b56958d590d596eaba5e781d896f7d9804baa))


## v1.0.5 (2021-05-21)

###  

* `__version__`-parsing fix, revert to `open()` ([`7e9b46c`](https://github.com/WIPACrepo/wipac-dev-tools/commit/7e9b46cdac798aded4afde51603243ff5d0e473d))


## v1.0.4 (2021-05-21)

###  

* pre-3.8 support patch ([`54478dc`](https://github.com/WIPACrepo/wipac-dev-tools/commit/54478dc25e338b03c83e353b4f222e715af3dfbb))


## v1.0.3 (2021-05-21)

###  

* SetupShop: A Supplemental `setup.py`/`setuptools.setup` Utility (#8) ([`736bca0`](https://github.com/WIPACrepo/wipac-dev-tools/commit/736bca00cb5a2a3f7e80ea5c9e1809c8ecd9fb69))

* Adding some build and test infrastructure ([`5351758`](https://github.com/WIPACrepo/wipac-dev-tools/commit/53517583f3cef944dddd6c3d1b0c7b7f353f1e27))


## v1.0.2 (2021-05-12)

###  

* Reexporting Fix for MyPy (#5) ([`6f22abd`](https://github.com/WIPACrepo/wipac-dev-tools/commit/6f22abd2e357ddb907e0d9351ba5117fe79b91b2))


## v1.0.1 (2021-05-12)

###  

* add `py.typed` (#4) ([`0857017`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0857017bb6f5adecbae90df0eb62b70e3071c387))


## v1.0.0 (2021-05-12)

### [minor]

* [minor] Add `from_environment()`

Last try at automating a major release.

BREAKING CHANGE: first major release ([`758b941`](https://github.com/WIPACrepo/wipac-dev-tools/commit/758b941b1a7cd7d0fd711ee9d1c9115c22260eac))


## v0.0.6 (2021-05-12)

###  

* major release ([`386faac`](https://github.com/WIPACrepo/wipac-dev-tools/commit/386faace076ebed68c687556e39f2dfa84ba62c2))


## v0.0.5 (2021-05-12)

###  

* BREAKING CHANGE: First Major Release ([`ec8cd84`](https://github.com/WIPACrepo/wipac-dev-tools/commit/ec8cd84b99b0387ca525a4a1177c430d59ccdc87))


## v0.0.4 (2021-05-12)

###  

* actual first major release

BREAKING CHANGE ([`c45f362`](https://github.com/WIPACrepo/wipac-dev-tools/commit/c45f3626560439a54d70aa10f1cc08fc06834775))


## v0.0.3 (2021-05-12)

###  

* first major release ([`351f595`](https://github.com/WIPACrepo/wipac-dev-tools/commit/351f595bbb6130ee40eee677b65094d12de46c63))


## v0.0.2 (2021-05-12)

###  

* Add `from_enviroment()` from `rest_tools` and Upgrade (#2) ([`09fb476`](https://github.com/WIPACrepo/wipac-dev-tools/commit/09fb476e4d473fef3a1796104c341dc996b5b0a2))


## v0.0.1 (2021-05-12)

###  

* Update setup.cfg ([`efa694d`](https://github.com/WIPACrepo/wipac-dev-tools/commit/efa694d9bee0b62c1783cffb128174436c296592))

* Update semantic-release.yml ([`04df4ec`](https://github.com/WIPACrepo/wipac-dev-tools/commit/04df4ec6b52904e6f6a26a850990b142740e387f))

* Add .circleci/config.yml (#3) ([`2152fdb`](https://github.com/WIPACrepo/wipac-dev-tools/commit/2152fdb1bca106da1327489f51c689ffaf83f17a))

* Merge pull request #1 from WIPACrepo/versioning ([`32e8f36`](https://github.com/WIPACrepo/wipac-dev-tools/commit/32e8f36e8867e81a5a0cee2765e19bcd782cd6c4))

* add `setup.py` &amp; `requirements.txt` ([`39441e4`](https://github.com/WIPACrepo/wipac-dev-tools/commit/39441e4c785ac19cc140ec40e485a5bc4f6f75fc))

* add `semantic-release.yml` ([`2edf85a`](https://github.com/WIPACrepo/wipac-dev-tools/commit/2edf85a822b36051afd8394aa327498efa0e5596))

* add `setup.cfg` ([`eb98b2e`](https://github.com/WIPACrepo/wipac-dev-tools/commit/eb98b2ec01b66e6448340a235974ea3d671462d3))

* add `__init__.py` ([`0e1b0b9`](https://github.com/WIPACrepo/wipac-dev-tools/commit/0e1b0b9d8ca60b847548ab40b54fbd48010d9dfa))

* Create README.md ([`4b966be`](https://github.com/WIPACrepo/wipac-dev-tools/commit/4b966bedebe187529d8e9582bd552457882c126b))

* Initial commit ([`4ba6661`](https://github.com/WIPACrepo/wipac-dev-tools/commit/4ba666162e7eda5bff1824ea88c2dcf5d28fdfa0))
