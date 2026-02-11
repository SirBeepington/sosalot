=== Doing some tests with Claude desktop

!!! Search functions were confusing: !!!

    find_files_by_name()
    find_files_by_name_recursive()
    search_file()

The distinction between "search by name" vs "search file content" wasn't immediately clear
I ended up using search_file() to search inside files, but the naming made me pause



!!! Pattern matching wasn't explained well: !!!

find_files_by_name() uses glob patterns, but examples were generic
Would have been helpful to know: "Use *error* to find files with 'error' anywhere in the name"
The case-insensitive matching was good but not prominently documented


!!! search_file can return a lot of data, MCP client specifying 'max_matches=100' in testing !!!

