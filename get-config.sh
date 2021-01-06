set -eu pipefail

#create kustomer config file
KUSTOMER_TOKEN=`echo $KUSTOMER_API_KEY | sed 's/[{}]//g' | sed 's/\"\"/\"/g'`
START_DATE="2020-12-01T00:00:00Z"
echo "{$KUSTOMER_TOKEN, \"start_date\": $START_DATE,\"user_agent\": \"tap-kustomer hanna.murphy@beam.dental\",\"date_window_size\": \"60\", \"page_size_limit\": \"100\"}" > /home/tap-kustomer/kustomer-config.json

#create kustomer state file
echo "{\"bookmarks\": {\"conversations\": \"\", \"customers\": \"\", \"kobjects\": \"\", \"messages\": \"\", \"shortcuts\": \"\", \"tags\": \"\", \"users\": \"\" }, \"currently_syncing\": \"\"}" > /home/tap-kustomer/kustomer-state.json

#create stitch config file
TOKEN=`echo $STITCH_TOKEN | sed 's/[{}]//g' | sed 's/\"\"/\"/g'`
echo "{\"client_id\": $STITCH_CLIENT_ID, $TOKEN,\"small_batch_url\": \"https://api.stitchdata.com/v2/import/batch\",\"big_batch_url\": \"https://api.stitchdata.com/v2/import/batch\",\"batch_size_preferences\": {}}" > /home/singer-dialpad/stitch-config.json

