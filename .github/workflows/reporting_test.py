import datetime as dt
import reporting

#
# Unit Test - DatesFromIssueTitle
def test_dates_from_issue_title():
    '''Tests the DatesFromIssueTitles function'''
    title = 'Contoso (12/30-12/31)'
    results = reporting.DatesFromIssueTitle(title)
    year = dt.date.today().year
    assert results['start'] == dt.date(year, 12, 30)
    assert results['finish'] == dt.date(year, 12, 31)

#
# Unit Test - CountChecklist
def test_count_checklist():
    '''Verified the CountChecklist function'''
    #region long string
    description = """
### Pre-engagement checklist
- [X] Task 1
- [ ] Task 2
- [x] Task 3
---

### Delivery checklist
- Planning call
  - [x] Address
  - [ ] Zoom or Teans

---

### Post-engagement checklist
- [ ] Issue closed and moved to the appropriate archive.
- [X] Testing complete
"""
#endregion

    results = reporting.CountChecklist(description)
    assert results['pre']['checked'] == 2
    assert results['pre']['unchecked'] == 1
    assert results['delivery']['checked'] == 1
    assert results['delivery']['unchecked'] == 1
    assert results['post']['checked'] == 1
    assert results['post']['unchecked'] == 1

    results = reporting.CountChecklist("Bad\nPre-engagement\nChecklist")
    assert results['pre'] is None
    assert results['delivery'] is None
    assert results['post'] is None

#
# Unit Test - FormatUrl
def test_format_url():
    '''Verifies the FormatUrl function'''
    results = reporting.FormatUrl('test-org', 'test-repo', 1)
    assert results == 'https://github.com/test-org/test-repo/issues/1'

    results = reporting.FormatUrl('', '', 0)
    assert results == 'https://github.com///issues/0'

#
# Unit Test - GetMondayDate
def test_get_monday_date():
    '''Verifies the GetMondayDate function'''
    # Sunday at midnight returns last Monday
    results = reporting.GetMondayDate(dt.date(2021, 7, 4))
    assert results == dt.date(2021, 6, 28)

    # Monday at mid-day returns today at midnight
    results = reporting.GetMondayDate(dt.datetime(2021, 7, 5, 12, 34, 56))
    assert results == dt.date(2021, 7, 5)

    # Tuesday at midnight returns the previous day
    results = reporting.GetMondayDate(dt.date(2021, 7, 6))
    assert results == dt.date(2021, 7, 5)

    # Current date/time returns a valid date in the past but less than 8-days in the past
    results = reporting.GetMondayDate() # Default param is now()
    assert results < dt.datetime.now().date()
    assert results > dt.datetime.now().date() - dt.timedelta(days=8)

#
# Unit Test - GetReportTitle
def test_get_report_title():
    '''Verifies the GetReportTitle function'''
    title = reporting.GetReportTitle()
    print(title)
    assert title.startswith('FastTrack Status Report (week of ')
    assert title.endswith(')')
    assert len(title) == len('FastTrack Status Report (week of ') + 11
