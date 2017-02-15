# Release process

## To release a new version of **anaconda-client**:

**1.)** Ensure you have the latest version from upstream and update your fork

    git pull upstream develop
    git push origin develop

**2.)** Update [CHANGELOG.md](https://github.com/Anaconda-Platform/anaconda-client/blob/develop/CHANGELOG.md), using loghub itself

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
