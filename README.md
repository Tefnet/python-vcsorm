# python-vcsorm

Version Control System (soon to be) Object Relational Mapper - VCS ORM.
Abstraction layer for VCS simulating Django ORM QuerySet API.
This project is using https://github.com/codeinn/vcs for multiple VCS support.

## Example usage

#### Filter (find) changesets in repository
To find changesets you can use filter method

    from datetime import datetime
    from vcsorm import VCSManager
    
    changesets = VCSManager('/path/to/your/repository').objects.filter(date__gt=datetime(2013,4,26))

    for changeset in changesets:
        print changeset.changed()

You can also chain filters

    changesets.filter(branch_name='newfeature')

    for changeset in changesets:
        print changeset.changed()

