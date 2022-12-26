#!/usr/bin/env bash
################################################################################
#                                                                              #
# Use this script to generate test data. Must be run as root from /home.       #
# Run `archy group1` to test the setup.                                        #
#                                                                              #
################################################################################

# Generic user data.
# We'll archive user1 and user2 as part of group1.
# User3 won't be archived as part of group2.
for i in {1..3}; do
    mkdir -p user$i/{Desktop,Documents,Downloads}
    useradd -d /home/user$i user$i
    touch user$i/Desktop/{test1.rtf,test2.pdf}
    touch user$i/Documents/{test3.odt,test4.xls}
    touch user$i/Downloads/{test5.py,test6.sh}
    chmod u+x user$i/Downloads/{test5.py,test6.sh}
    chown -R user$i:user$i /home/user$i
done

# Group data
for j in 1 2; do
    groupadd group$j
    mkdir -p group$j/{project,tests}
    touch group$j/project/{__init__,foo,bar}.py
    touch group$j/tests/{__init__,test_foo,test_bar}.py
    chown -R root:group$j group$j
    chmod -R g+w group$j
done

usermod -aG group1 user1
usermod -aG group1 user2
usermod -aG group2 user3
# Archive these files
chown -R user1:group1 group1/project
chown -R user2:group1 group1/tests
# Don't archive these files
chown -R user3:group2 group2/project
chown -R user3:group2 group2/tests

for j in 1 2; do
    touch group$j/project/baz.py
    touch group$j/tests/test_baz.py
done
# These files should be archived
for filename in 'group1/project/baz.py' 'group1/tests/test_baz.py'; do
    chown user3:group1 $filename
done
# These files should not be archived
touch user1/admin_flag.txt
for filename in 'group2/project/baz.py' 'group2/tests/test_baz.py'; do
    chown user2:group2 $filename
done
