import sys
import datetime
import shutil
import string
import collections
import pkg_resources
from optparse import OptionParser

from .manager import VCSManager, VCSFileDiff
from .decorators import IterStreamer

class VCSReport(object):
    def __init__(self, manager, *args, **kwargs):
        if isinstance(manager, basestring):
            self._manager = VCSManager(manager)
        else:
            self._manager = manager

        self._cs = []

    def fetch_changesets(self, *args, **kwargs):
        raise NotImplementedError
        
    def render(self):
        raise NotImplementedError

    def render_to_file(self, output_file):
        if isinstance(output_file, basestring):
            output_file = file(output_file, 'w')
            close_file = True

        shutil.copyfileobj(self.render(), output_file)

        if close_file:
            output_file.close()

    def render_template(self, filename, **kwargs):
        # 
        # Hopefully it won't be a big file
        # TODO: Use real template engine
        f = open(filename)
        rvt = string.Template(f.read())
        f.close()
        rv = rvt.substitute(**kwargs)
        # Sometimes this is unicode, sometimes str ?!
        if isinstance(rv, unicode):
            return rv.encode('utf-8')
        else:
            return rv

class VCSDailyReport(VCSReport):
    SINGLE_HEADER_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/single_header.html')
    SINGLE_FOOTER_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/single_footer.html')
    SINGLE_CHANGESET_TOP_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/single_changeset_top.html')
    SINGLE_CHANGESET_BOTTOM_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/single_changeset_bottom.html')
    SINGLE_FOOTER_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/single_footer.html')
    COMMITTER_TAB_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/committer_tab.html')
    DIFFSTAT_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/diffstat.html')
    DIFFSTAT_DESC_TEMPLATE = pkg_resources.resource_filename('vcsorm','static/templates/diffstat_desc.html')
    SIMPLETABS_JS = pkg_resources.resource_filename('vcsorm','static/js/simpletabs_1.3.js')
    SIMPLETABS_CSS = pkg_resources.resource_filename('vcsorm','static/css/simpletabs.css')
    CSS_CUSTOM = pkg_resources.resource_filename('vcsorm','static/css/style.css')

    def __init__(self, manager, start_date, end_date=None, url_prefix=None):
        super(VCSDailyReport, self).__init__(manager)
        self.start_date = start_date
        self.end_date = end_date if end_date else self.start_date+datetime.timedelta(days=1)
        self.url_prefix = url_prefix if url_prefix else "#"

    def fetch_changesets(self, *args, **kwargs):
        return self._manager.objects.filter(date__range=[self.start_date, self.end_date]).order_by('committer_name')

    @IterStreamer
    def render(self):
        yield self.render_template(
            self.SINGLE_HEADER_TEMPLATE,
            vcsorm_simpletabs_js_content = self.render_template(self.SIMPLETABS_JS),
            vcsorm_simpletabs_css_content = self.render_template(self.SIMPLETABS_CSS),
            vcsorm_css_content = self.render_template(self.CSS_CUSTOM),
        )
        committers = collections.OrderedDict()
        filelink_id = 0
        committer_diffstat = {'added':0,'removed':0}
        for cs in self.fetch_changesets():
            if cs.committer_name not in committers.keys():
                if committers:
                    # Next committer, close tab
                    yield self.render_template(
                        self.SINGLE_CHANGESET_BOTTOM_TEMPLATE,
                        vcsorm_changedfiles=vcsorm_changedfiles,
                        vcsorm_added=committer_diffstat['added'],
                        vcsorm_removed=committer_diffstat['removed'],
                    )
                committer_diffstat = committers[cs.committer_name] = {'added':0,'removed':0}
                vcsorm_changedfiles = ""
                yield self.render_template(self.SINGLE_CHANGESET_TOP_TEMPLATE)

            vcsorm_changedfiles += self.render_template(self.DIFFSTAT_DESC_TEMPLATE,
                                                        message=cs.message,
                                                        url_prefix=self.url_prefix,
                                                        cid=cs.raw_id)

            for csf in cs.changed():
                diff = VCSFileDiff(csf)
                added, removed = diff.stats()
                diffstat = {
                    'path': diff.path,
                    'added': added,
                    'removed': removed,
                    'linkname': '',
                    'filelink': filelink_id,
                }

                committer_diffstat['added']+=added
                committer_diffstat['removed']+=removed

                diffstat['linkname'] = diffstat['filelink']
                yield self.render_template(self.DIFFSTAT_TEMPLATE, **diffstat)
                yield diff.as_html().encode('utf-8')

                vcsorm_changedfiles += self.render_template(self.DIFFSTAT_TEMPLATE, **diffstat)
                filelink_id+=1

        if committers:
            # Close last tab
            yield self.render_template(
                self.SINGLE_CHANGESET_BOTTOM_TEMPLATE,
                vcsorm_changedfiles=vcsorm_changedfiles,
            )
        vcsorm_committers_tabs = ""
        for committer,stats in committers.iteritems():
            vcsorm_committers_tabs += self.render_template(
                                            self.COMMITTER_TAB_TEMPLATE,
                                            vcsorm_committer = committer,
                                            vcsorm_added = stats['added'],
                                            vcsorm_removed = stats['removed'],
                                      )
        
        yield self.render_template(self.SINGLE_FOOTER_TEMPLATE, vcsorm_committers_tabs=vcsorm_committers_tabs)

    @classmethod        
    def run(cls):
        parser = OptionParser()
        parser.add_option("-r", "--repository", dest="repo_directory",
                  help="write report to DIR", metavar="DIR", default='.')
        parser.add_option("-f", "--file", dest="filename",
                  help="write report to FILE", metavar="FILE", default='vcs_report.html')
        parser.add_option("-d", "--date",
                  action="store", dest="date", default=str(datetime.date.today()),
                  help="report date")
        parser.add_option("-u", "--url-prefix",
                  action="store", dest="url_prefix", default="",
                  help="report date")

        (options, args) = parser.parse_args()

        if " " in options.date:
            start_date, end_date = options.date.split(' ',2)
            start_date = datetime.datetime.strptime(start_date, '%Y-%m-%d')
            end_date = datetime.datetime.strptime(end_date, '%Y-%m-%d')
        else:
            start_date = datetime.datetime.strptime(options.date, '%Y-%m-%d')
            end_date = None

        cls(options.repo_directory,
            start_date=start_date,
            end_date=end_date,
            url_prefix=options.url_prefix
        ).render_to_file(options.filename)

