#pragma once 

struct FREQ_ITEM
{
	int nitem;
	int nsup;
};

struct HEADER_NODE
{
	int nitem;
	int nsup;
	int num_of_rdnt_items;
	int* prdnt_items;
};
typedef HEADER_NODE* HEADER_TABLE;

extern FREQ_ITEM* gpfreqitems;
extern int gnum_of_freqitems;
extern int* gpitem_order_map;
extern int* gpprefix_itemset;
extern int gnprefix_len;
extern int* gpcover_items;
extern int gnum_of_cover_items;
extern unsigned int gnmap_value;
extern int* gpitem_bitmap;

extern int gnmax_key_len;
extern int gnmax_item_id;
extern int gndb_size;

extern double gdtotal_pats;
extern int gnmax_pat_len;
extern int* gpstack;

extern bool *gprdnt_flags;
extern int gntotal_rdnt_items;
extern int *gprdnt_item_positions;
extern int gnrdnt_item_num;

extern int gnrep_type;

void RecoverFI(char* szfreqkey_filename, char* szfreqbd_filename, char* szcoveritem_filename, char* szoutput_filename);


int comp_freqitems(const void* e1, const void* e2);
int comp_headernodes(const void* e1, const void* e2);

extern HEADER_TABLE gpdfs_header_array;
extern int gndfs_header_size;
extern int gndfs_header_pos;

inline HEADER_TABLE NewHeaderTable(int num_of_freqitems)
{
	HEADER_TABLE pheader_table;

	if(gndfs_header_pos+num_of_freqitems<=gndfs_header_size)
	{
		pheader_table = &(gpdfs_header_array[gndfs_header_pos]);
		gndfs_header_pos += num_of_freqitems;
	}
	else 
		pheader_table = new HEADER_NODE[num_of_freqitems];

	return pheader_table;
}

inline void DelHeaderTable(HEADER_TABLE pheader_table, int num_of_freqitems)
{
	if((unsigned int)pheader_table>=(unsigned int)gpdfs_header_array && (unsigned int)pheader_table<(unsigned int)gpdfs_header_array+sizeof(HEADER_NODE)*gndfs_header_size)
		gndfs_header_pos -= num_of_freqitems;
	else
		delete []pheader_table;
}


#define PAGE_SIZE (1<<15)
struct INT_PAGE
{
	int ppage[PAGE_SIZE];
	INT_PAGE *pnext;
};
struct INT_PAGE_BUF
{
	INT_PAGE *phead;
	INT_PAGE *pcur_page;
	int ncur_pos;
	int ntotal_pages;
};
extern INT_PAGE_BUF gordnt_item_buf;

inline INT_PAGE* NewIntPage()
{
	INT_PAGE *ppage;

	ppage = new INT_PAGE;
	ppage->pnext = NULL;

	return ppage;
}
inline void DelIntPage(INT_PAGE *ppage)
{
	delete ppage;
}
inline int* NewOneIntArray(int length)
{
	INT_PAGE *pnew_page;
	int *parray;

	if(gordnt_item_buf.ncur_pos+length>PAGE_SIZE)
	{
		if(gordnt_item_buf.pcur_page->pnext==NULL)
		{
			pnew_page = NewIntPage();
			gordnt_item_buf.pcur_page->pnext = pnew_page;
			gordnt_item_buf.pcur_page = pnew_page;
			gordnt_item_buf.ntotal_pages++;
		}
		else
			gordnt_item_buf.pcur_page = gordnt_item_buf.pcur_page->pnext;
		gordnt_item_buf.ncur_pos = 0;
	}

	parray = &(gordnt_item_buf.pcur_page->ppage[gordnt_item_buf.ncur_pos]);
	gordnt_item_buf.ncur_pos += length;

	return parray;
}

void DelIntBuf(INT_PAGE_BUF *prdnt_item_buf);


