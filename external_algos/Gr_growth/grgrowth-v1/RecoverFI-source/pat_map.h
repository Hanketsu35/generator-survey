#pragma once

#include <stdio.h>

#define MAP_SIZE 1299709
//#define MAP_SIZE 1372549
//#define MAP_SIZE 2135957

#define ITEM_HASH_BITMAP  0x001f

typedef int ITEM;

struct PATTERN
{
	int nlen;
	int nsup;
	ITEM *pitemset;
	unsigned int nmap_value;
};

struct PAT_MAP_NODE
{
	PATTERN *ppattern;
	PAT_MAP_NODE *pnext;
};

class PAT_MAP
{
	PAT_MAP_NODE** mppat_map;
	PAT_MAP_NODE* mpmap_node_buf;
	int mnpat_map_size;
	int mnmap_buf_pos;
	PATTERN* mppatterns;
	ITEM* mppat_buf;
	int mnsearch_times;
	double mdavg_search_depth;

	int LoadFG(char * szfreqkey_filename, PATTERN* &ppatterns, ITEM* &ppat_buf);
	int LoadFreqBdPats(char* szfreqbd_filename, PATTERN* &ppatterns, ITEM* &ppat_buf);
	int LoadNegBdPats(char* szfreqbd_filename, PATTERN* &ppatterns, ITEM* &ppat_buf);
	void InsertOnePat(PATTERN *ppat);

	unsigned int HashFunc(unsigned int nmap_value);

public:

	int mnum_of_pats;

	void BuildPatHashMap(char* szpat_filename, int npat_type);
	void DelPatMap();

	int SearchPat(int npat_len);

};

extern PAT_MAP gofreqkey_map;
extern PAT_MAP gobd_map;
extern int gnrdnt_item_pos;

inline unsigned int HashAdd1Item(unsigned int nmap_value, int nitem)
{
	return (unsigned int)(nmap_value+(1<<(gpitem_order_map[nitem]&ITEM_HASH_BITMAP))+gpitem_order_map[nitem]+(1<<(nitem&ITEM_HASH_BITMAP))+nitem+1);
}

inline unsigned int HashRemove1Item(unsigned int nmap_value, int nitem)
{
	return (unsigned int)(nmap_value-(1<<(gpitem_order_map[nitem]&ITEM_HASH_BITMAP))-gpitem_order_map[nitem]-(1<<(nitem&ITEM_HASH_BITMAP))-nitem-1);
}

inline unsigned int HashItemset(ITEM *pitemset, int length)
{
	unsigned int nmap_value;
	int i;

	nmap_value = 0;
	for(i=0;i<length;i++)
		nmap_value = HashAdd1Item(nmap_value, pitemset[i]);

	return nmap_value;
}

inline int GetNextNum(FILE *fp)
{
	char ch;
	int nnum;

	nnum = 0;
	ch = fgetc(fp);
	while(!feof(fp) && ch>='0' && ch<='9')
	{
		nnum = nnum*10 + ch-'0';
		ch = fgetc(fp);
	}
	return nnum;
}

