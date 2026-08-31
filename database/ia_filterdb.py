import logging
import re
from pymongo.errors import DuplicateKeyError
from umongo import Instance, Document, fields
from marshmallow.exceptions import ValidationError
from database.mongo import create_motor_client
from info import DATABASE_URI, DATABASE_NAME, COLLECTION_NAME, USE_CAPTION_FILTER

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


client = create_motor_client(DATABASE_URI)
db = client[DATABASE_NAME]
instance = Instance.from_db(db)

@instance.register
class Media(Document):
    file_id = fields.StrField(required=True)
    file_ref = fields.StrField(allow_none=True)
    file_name = fields.StrField(required=True)
    file_size = fields.IntField(required=True)
    file_type = fields.StrField(allow_none=True)
    mime_type = fields.StrField(allow_none=True)
    caption = fields.StrField(allow_none=True)
    file_unique_id = fields.StrField(required=True, unique=True)

    class Meta:
        indexes = ('$file_name', )
        collection_name = COLLECTION_NAME


async def save_file(media):
    """Save file in database"""

    file_id = media.file_id
    file_unique_id = getattr(media, "file_unique_id", media.file_id)
    file_name = re.sub(r"(_|\-|\.|\+)", " ", str(media.file_name)) if media.file_name else ""
    try:
        file = Media(
            file_id=file_id,
            file_unique_id=file_unique_id,
            file_name=file_name,
            file_size=media.file_size,
            file_type=media.file_type,
            mime_type=media.mime_type,
            caption=media.caption.html if media.caption else None,
        )
    except ValidationError:
        logger.exception('Error occurred while saving file in database')
        return False, 2
    else:
        try:
            await file.commit()
        except DuplicateKeyError:      
            logger.warning(
                f'{getattr(media, "file_name", "NO_FILE")} is already saved in database'
            )

            return False, 0
        else:
            logger.info(f'{getattr(media, "file_name", "NO_FILE")} is saved to database')
            return True, 1



async def get_search_results(
    query,
    file_type=None,
    max_results=10,
    offset=0,
    filter=False,
    include_caption=False,
):
    """For given query return (results, next_offset)"""

    query = query.strip()[:160]
    # Treat quoted phrases as one term and require every term to match either
    # the filename or caption. Escaping each term prevents regex injection and
    # makes searches such as "movie 2025 1080p" order-independent.
    terms = [
        (quoted or word).strip()
        for quoted, word in re.findall(r'"([^"]+)"|(\S+)', query)
        if (quoted or word).strip()
    ][:8]

    if not terms:
        # An empty browse query means every indexed record, including Telegram
        # videos that do not have a file_name.
        filter = {}
    else:
        clauses = []
        for term in terms:
            pattern = re.escape(term).replace(r'\ ', r'[\s.\+_-]+')
            regex = re.compile(pattern, flags=re.IGNORECASE)
            if USE_CAPTION_FILTER or include_caption:
                clauses.append({'$or': [{'file_name': regex}, {'caption': regex}]})
            else:
                clauses.append({'file_name': regex})
        filter = clauses[0] if len(clauses) == 1 else {'$and': clauses}

    if file_type:
        filter['file_type'] = file_type

    total_results = await Media.count_documents(filter)
    next_offset = offset + max_results

    if next_offset >= total_results:
        next_offset = ''

    cursor = Media.find(filter)
    # Sort by recent
    cursor.sort('$natural', -1)
    # Slice files according to offset and max results
    cursor.skip(offset).limit(max_results)
    # Get list of files
    files = await cursor.to_list(length=max_results)

    return files, next_offset, total_results



async def get_file_details(query):
    try:
        from bson.objectid import ObjectId
        filter = {'_id': ObjectId(query)}
    except:
        filter = {'file_id': query}
    cursor = Media.find(filter)
    filedetails = await cursor.to_list(length=1)
    return filedetails


