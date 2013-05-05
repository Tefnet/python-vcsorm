import logging
import re
import shutil
from datetime import datetime
import difflib

import vcs


#pkg_resources.resource_filename('vcsorm','conf')
HTMLDiffProcessor = difflib.HtmlDiff(tabsize=4, wrapcolumn=80)

class VCSFileDiff(object):
    htmldiff = HTMLDiffProcessor
    def __init__(self, fnode_cur, fnode_prev=None):
        self._fnode_cur = fnode_cur
        self._fnode_prev = fnode_prev if fnode_prev else self.revision_prev(self._fnode_cur)
        self._stats_added = 0
        self._stats_removed = 0

    def revision_prev(self, fnode):
        """
        Get previous revision of FileNode
        """
        history = fnode.history
        # TODO: Handle fnode from merge (won't be in history)
        # TODO: Handle IndexError (if fnode is in oldest revision)
        try:
            return history[history.index(fnode.changeset)+1].get_node(fnode.path)
        except ValueError:
            # FIXME: Fails during date range 2013-04-24 - 2013-05-04
            logging.error('Could not find %s for filenode %s  in history!', fnode.changeset, fnode)
            return fnode.changeset.prev().get_node(fnode.path)

    @property
    def path(self):
        return self._fnode_cur.path

    def stats(self):
        """
        Diff stats
        Returns info about lines added/removed
        """
        if self._stats_added or self._stats_removed:
            return (self._stats_added, self._stats_removed)

        for line in self.as_plain():
            if line.startswith('+'):
                self._stats_added += 1
            elif line.startswith('-'):
                self._stats_removed += 1
        
        return (self._stats_added, self._stats_removed)

    def as_plain(self):
        # TODO: Cache fnode.content.split ? (also needed for as_html)
        #

        return difflib.ndiff(
                self._fnode_prev.content.split('\n'),
                self._fnode_cur.content.split('\n')
        )

    def as_html(self):
        """
        Return side by side diff as HTML table
        """
        return self.htmldiff.make_table(
            self._fnode_prev.content.split('\n'),
            self._fnode_cur.content.split('\n'),
            self._fnode_prev.path,
            self._fnode_cur.path,
            context=True
        )
        

class VCSQuerySet(object):
    _filter_vcs_keys = ('date', 'branch_name')
    _filter_seq_keys = ('committer', 'committer_name', 'committer_email')
    _filter_keys = _filter_vcs_keys + _filter_seq_keys
    _manager = None
    def __init__(self, manager):
        self._manager = manager
        self._cs = None
        self._vcs_filter = {}
        self._seq_filter = {}
        self._seq_order = {}
    
    def __iter__(self):

        for item in self.cs:
            if len(item.parents)>1:
                # TODO: merges not supported yet
                continue
            yield item
        

        # TODO: _filter_seq (filter during sequential scan) support
        # Move to def cs(..) ?
        #for cs in self.cs:
        #    #if cs.committer_email == 'foo@bar.com'
        #    yield cs

    @property
    def repo(self):
        return self._manager.repo

    @property
    def cs(self):
        if not getattr(self, '_cs'):
            self._cs = self.repo.get_changesets(**self.vcs_filter)
            if getattr(self, '_seq_order'):
                self._cs = sorted(self._cs, key=lambda item: item.committer_name)
        return self._cs

    @property
    def vcs_filter(self):
        return self._vcs_filter

    def all(self):
        return [cs for cs in self]

    def parse_filter(self, **kwargs):
        for ikey,ival in kwargs.iteritems():

            if '__' in ikey:
                key,oper = ikey.split('__')
            else:
                key = ikey
                oper = 'eq'

            if key not in self._filter_keys:
                continue

            if key == 'date':
                if oper == 'range':
                    self._vcs_filter.update({
                        'start_date': ival[0],
                        'end_date': ival[1]
                    })
                elif oper in ['gt','lt']:
                    self._vcs_filter.update({
                        ('start' if oper=='gt' else 'end') + '_date': ival
                    })
            elif key == 'branch_name':
                self._vcs_filter.update({key:ival})
            elif key in self._filter_seq_keys:
                self._seq_filter[(key,oper)] = ival

    def filter(self, **kwargs):
        """
        Filter query results. 
        Arguments are similar to Django ORM. For example:
        * query changesets past 2013.04.14
        .filter(date__gt=datetime.datetime(2013,04,14))
        
        * query changesets between 2013.04.14 and 2013.04.26
        .filter(date__range=[datetime.datetime(2013,04,14), datetime.datetime(2013,04,26)])

        * you can also chain filters
        .filter(date__gt=datetime.datetime(2013,04,14)).filter(branch_name='new_feature')

        Result of filter function is a VCSQuerySet which you can iterate (fetching each changeset at a time)
        or use .all() to fetch all changesets at once (as a list)
        """
        self.parse_filter(**kwargs)
        return self

    def order_by(self, *args):
        # TODO: write real ordering
        # Right now it is fake ordering (only commiter_name supported)
        self._seq_order = {'commiter_name': 'ASC'}
        # Invalidate changeset result
        if getattr(self, '_cs'):
            self._cs = None
        return self

class VCSManager(object):
    queryset_cls = VCSQuerySet
    def __init__(self, path):
        self._path = path
        self.repo = vcs.get_repo(path=self._path)

    def get_queryset(self):
        return self.queryset_cls(manager=self)

    @property
    def objects(self):
        return self.get_queryset()

