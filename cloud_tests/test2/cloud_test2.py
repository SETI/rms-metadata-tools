# gcloud auth application-default login       # if necessary

# python3 cloud_test2.py
# sep;gsutil cat gs://rms-metadata-jspitale/xxx/yyy/zzz/aaa/bbb/test.txt




# cloud_tasks run --config config2.yaml --task-file test2_tasks.json -vv
# sep;gsutil cat gs://rms-metadata-jspitale/xxx/yyy/zzz/aaa/bbb/test.txt




#from filecache import FCPath
#FCPath('gs://rms-metadata-jspitale/test.txt').write_text('Hello\nWorld\n', encoding='utf-8')
#exit()


from filecache import FCPath

#filespec = FCPath('gs://rms-metadata-jspitale/test.txt')
filespec = FCPath('gs://rms-metadata-jspitale/xxx/yyy/zzz/aaa/bbb/test.txt')
if filespec.exists():
    content = filespec.read_text(encoding='utf-8')
    filespec.write_text(content + '\nGoodbye\nWorld\n', encoding='utf-8')
    exit()

filespec.write_text('Hello\nWorld\n', encoding='utf-8')
exit()



