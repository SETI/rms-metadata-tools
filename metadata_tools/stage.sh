#! /bin/bash
################################################################################
# stage.sh
#
#  Copy metadata collection from test directories to staging directories.
#
#     Run from the top of the collection test tree, e.g.:
#
#         $RMS_METADATA_TEST/GO_0xxx/
#
#     New metadata tables and labels are copied to:
#
#         $RMS_METADATA_STAGE/<collection>/current/
#
#     Existing files are copied to:
#
#         $RMS_METADATA_STAGE/<collection>/previous/
#
################################################################################

# Collection is current dir name
pwd=`pwd`
parts=($(echo $pwd | tr "/" " "))
col=${parts[-1]}

parts=($(echo $col | tr "_" " "))
pfx=${parts[0]}

cur=$RMS_METADATA_STAGE/$col/current
prev=$RMS_METADATA_STAGE/$col/previous

# Move current files to previous
rm -rf $prev
if [ -d $cur ]; then
  mv -f $cur $prev
fi

# Copy new files to current
mkdir -p $cur
for dir in $pfx*
do
    mkdir $cur/"$dir"
    cp $dir/GO* $cur/"$dir"
done




