#include "arinc.h"

#include <string.h>    // memset, memcpy, strlen
#include <arpa/inet.h> // htonl, htons, ntohl, ntohs

#include "esp_log.h"

static const char *TAG = "arinc";

int init_lui(lui_data_t *lui, arinc_op_status_code_t status_code, const char *description)
{
    if (!lui || !description)
    {
        ESP_LOGE(TAG, "Invalid parameters for LUI initialization");
        return -1;
    }

    // Zero out the structure
    memset(lui, 0, sizeof(lui_data_t));

    // Set fixed values
    lui->file_length = htonl(sizeof(lui_data_t));
    memcpy(lui->protocol_version, "A4", 2);

    // Set status code (convert to network byte order)
    lui->status_code = htons(status_code);

    // Set description and its length
    size_t desc_len = strlen(description);
    if (desc_len > sizeof(lui->description) - 1)
    {
        desc_len = sizeof(lui->description) - 1;
    }
    lui->desc_length = desc_len;
    memcpy(lui->description, description, desc_len);
    lui->description[desc_len] = '\0';

    ESP_LOGI(TAG, "LUI initialized: status=%04x, desc='%s'",
             status_code, lui->description);

    return 0;
}

int init_lus(lus_data_t *lus, arinc_op_status_code_t status_code,
             const char *description, uint16_t counter, const char *ratio)
{
    if (!lus || !description || !ratio)
    {
        ESP_LOGE(TAG, "Invalid parameters for LUS initialization");
        return -1;
    }

    if (strlen(ratio) != 3)
    {
        ESP_LOGE(TAG, "Invalid ratio format (must be 3 characters)");
        return -1;
    }

    // Zero out the structure
    memset(lus, 0, sizeof(lus_data_t));

    // Set fixed values
    lus->file_length = htonl(sizeof(lus_data_t));
    memcpy(lus->protocol_version, "A4", 2);

    // Set status code (convert to network byte order)
    lus->status_code = htons(status_code);

    // Set description and its length
    size_t desc_len = strlen(description);
    if (desc_len > sizeof(lus->description) - 1)
    {
        desc_len = sizeof(lus->description) - 1;
    }
    lus->desc_length = desc_len;
    memcpy(lus->description, description, desc_len);
    lus->description[desc_len] = '\0';

    // Set counter (convert to network byte order)
    lus->counter = htons(counter);

    // Set timers to 0 (already done by memset)
    lus->exception_timer = 0;
    lus->estimated_time = 0;

    // Set progress ratio
    memcpy(lus->load_list_ratio, ratio, 3);

    ESP_LOGI(TAG, "LUS initialized: status=%04x, counter=%d, ratio=%s",
             status_code, counter, ratio);

    return 0;
}

int parse_lur(const uint8_t *buf, size_t len, lur_data_t *out)
{
    if (!buf || !out || len < 8)
    { // minimal: file_length(4) + proto(2) + num_headers(2)
        ESP_LOGE(TAG, "parse_lur: invalid parameters or buffer too small");
        return -1;
    }

    const uint8_t *p = buf;
    size_t remaining = len;

    // file_length (4)
    if (remaining < 4)
        return -1;
    uint32_t file_length = ntohl(*(uint32_t *)p);
    p += 4;
    remaining -= 4;

    // protocol version (2)
    if (remaining < 2)
        return -1;
    char proto[3] = {0};
    memcpy(proto, p, 2);
    p += 2;
    remaining -= 2;

    // num_header_files (2)
    if (remaining < 2)
        return -1;
    uint16_t num_headers = ntohs(*(uint16_t *)p);
    p += 2;
    remaining -= 2;

    // We'll only parse the first header file and load part number
    if (num_headers == 0)
    {
        ESP_LOGW(TAG, "parse_lur: num_headers == 0");
        return -1;
    }

    // header file length (1)
    if (remaining < 1)
        return -1;
    uint8_t header_len = *p++;
    remaining -= 1;
    if (header_len > remaining)
        return -1;

    size_t hlen = header_len;
    if (hlen > sizeof(out->header_filename) - 1)
        hlen = sizeof(out->header_filename) - 1;
    memcpy(out->header_filename, p, hlen);
    out->header_filename[hlen] = '\0';
    out->header_file_length = (uint8_t)header_len;
    p += header_len;
    remaining -= header_len;

    // load part number length (1)
    if (remaining < 1)
        return -1;
    uint8_t pn_len = *p++;
    remaining -= 1;
    if (pn_len > remaining)
        return -1;

    size_t plen = pn_len;
    if (plen > sizeof(out->load_part_number) - 1)
        plen = sizeof(out->load_part_number) - 1;
    memcpy(out->load_part_number, p, plen);
    out->load_part_number[plen] = '\0';
    out->load_part_number_length = (uint8_t)pn_len;
    p += pn_len;
    remaining -= pn_len;

    // Fill remaining fixed fields in network byte order
    out->file_length = htonl(file_length);
    memcpy(out->protocol_version, proto, 2);
    out->num_header_files = htons(num_headers);

    ESP_LOGI(TAG, "parse_lur: parsed header='%s' part='%s'", out->header_filename, out->load_part_number);
    return 0;
}
