# Release Checklist
- [ ] Release to beta
- [ ] Email Aamna about the beta release
- [ ] Update Internal Change Log: https://github.com/Anaconda-Server/anaconda-server/blob/develop/CHANGELOG.md
- [ ] If docs changed, coordinate release with Kerry
- [ ] Release to production
  - [ ] Ensure static assets are released as needed
- [ ] Create this ticket for next release and put it in the backlog
- [ ] Update the label to the installer on anaconda cloud (https://anaconda.org/binstar/binstar-server/files)

# Include CLI Client
- [ ] If Anaconda-Client changes then release with other changes

# Minor Release
- [ ] Update Public Docs Landing Page - http://docs.continuum.io/anaconda-server/index
      source: https://github.com/ContinuumIO/docs/blob/master/build/anaconda-server/index.rst
- [ ] Update Public Docs Change Log - http://docs.continuum.io/anaconda-server/changelog
- [ ] Post to @ everyone in FlowDock with an update announcing the release and providing the short summary of changes


# Release process (deprecated?)

## To release a new version of **anaconda-client**:

**1.)** Ensure you have the latest version from upstream and update your fork

    git pull upstream develop
    git push origin develop

**2.)** Update [CHANGELOG.md](https://github.com/Anaconda-Platform/anaconda-client/blob/develop/CHANGELOG.md), using [loghub](https://github.com/spyder-ide/loghub) 

    loghub Anaconda-Platform/anaconda-client --since-tag <latest-version-tag-used> -u <username> -ilr "reso:completed" -ilg "type:feature" "New Features" -ilg "type:enhancements" "Code Enhancements" -ilg "type:bug" "Bugs fixed"

**3.)** Commit changes for changelog update

    git add .
    git commit -m "Update changelog for release X.X.X"

**4.)** Add release tag

    git tag -a X.X.X -m 'Release version'

**5.)** Push changes
    
    git push upstream develop
    git push origin develop
    git push --tags

**6.)** Inform build team that new release is available

