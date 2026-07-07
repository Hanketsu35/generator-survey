#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/timeb.h>

#include "global.h"
#include "pat_map.h"

PAT_MAP gofreqkey_map;
PAT_MAP gobd_map;
int gnrdnt_item_pos;

int PAT_MAP::LoadFG(char * szfreqkey_filename, PATTERN* &ppatterns, ITEM* &ppat_buf)
{
	FILE *fp;
	int npat_len, nitem, npat_sup, num_of_pats, nbuf_size, nbuf_pos, i;

	fp = fopen(szfreqkey_filename, "rt");
	if(fp==NULL)
	{
		printf("Error: cannot open file %s for read\n", szfreqkey_filename);
		return 0;
	}

	num_of_pats = 0;
	nbuf_size = 0;
	gnmax_key_len = 0;
	gnum_of_freqitems = 0;
	gnmax_item_id = 0;

	npat_len = GetNextNum(fp);
	while(!feof(fp))
	{
		if(gnmax_key_len<npat_len)
			gnmax_key_len = npat_len;
		for(i=0;i<npat_len;i++)
			nitem = GetNextNum(fp);
		npat_sup = GetNextNum(fp);
		if(npat_len==1)
		{
			gnum_of_freqitems++;
			if(gnmax_item_id<nitem)
				gnmax_item_id = nitem;
		}
		else if(npat_len==0)
			gndb_size = npat_sup;
		num_of_pats++;
		nbuf_size += npat_len;

		npat_len = GetNextNum(fp);
	}
	rewind(fp);

	gnmax_key_len++;
	gnmax_item_id++;

	ppatterns = new PATTERN[num_of_pats];
	ppat_buf = new ITEM[nbuf_size];
	nbuf_pos = 0;
	num_of_pats = 0;
	gpfreqitems = new FREQ_ITEM[gnum_of_freqitems];
	gnum_of_freqitems = 0;

	npat_len = GetNextNum(fp);
	while(!feof(fp))
	{
		ppatterns[num_of_pats].nlen = npat_len;
		ppatterns[num_of_pats].pitemset = &(ppat_buf[nbuf_pos]);
		nbuf_pos += npat_len;
		for(i=0;i<npat_len;i++)
			ppatterns[num_of_pats].pitemset[i] = GetNextNum(fp);
		ppatterns[num_of_pats].nsup = GetNextNum(fp);
		if(npat_len==1)
		{
			gpfreqitems[gnum_of_freqitems].nitem = ppatterns[num_of_pats].pitemset[0];
			gpfreqitems[gnum_of_freqitems].nsup = ppatterns[num_of_pats].nsup;
			gnum_of_freqitems++;
		}
		num_of_pats++;

		npat_len = GetNextNum(fp);
	}
	fclose(fp);

	qsort(gpfreqitems, gnum_of_freqitems, sizeof(FREQ_ITEM), comp_freqitems);
	gpitem_order_map = new int[gnmax_item_id];
	memset(gpitem_order_map, -1, sizeof(int)*gnmax_item_id);
	for(i=0;i<gnum_of_freqitems;i++)
		gpitem_order_map[gpfreqitems[i].nitem] = i;

	return num_of_pats;
}

int PAT_MAP::LoadFreqBdPats(char* szfreqbd_filename, PATTERN* &ppatterns, ITEM* &ppat_buf)
{
	FILE *fp;
	int npat_len, nitem, npat_sup, num_of_pats, nbuf_size, nbuf_pos, i;

	fp = fopen(szfreqbd_filename, "rt");
	if(fp==NULL)
	{
		printf("Error: cannot open file %s for read\n", szfreqbd_filename);
		return 0;
	}

	num_of_pats = 0;
	nbuf_size = 0;

	npat_len = GetNextNum(fp);
	while(!feof(fp))
	{
		for(i=0;i<npat_len;i++)
			nitem = GetNextNum(fp);
		npat_sup = GetNextNum(fp);
		if(npat_len==1)
			gpcover_items[gnum_of_cover_items++] = nitem;
		num_of_pats++;
		nbuf_size += npat_len;

		npat_len = GetNextNum(fp);
	}
	rewind(fp);
	if(num_of_pats==0)
	{
		fclose(fp);
		return 0;
	}

	ppatterns = new PATTERN[num_of_pats];
	ppat_buf = new ITEM[nbuf_size];
	nbuf_pos = 0;
	num_of_pats = 0;

	npat_len = GetNextNum(fp);
	while(!feof(fp))
	{
		ppatterns[num_of_pats].nlen = npat_len;
		ppatterns[num_of_pats].pitemset = &(ppat_buf[nbuf_pos]);
		nbuf_pos += npat_len;
		for(i=0;i<npat_len;i++)
			ppatterns[num_of_pats].pitemset[i] = GetNextNum(fp);
		ppatterns[num_of_pats].nsup = GetNextNum(fp);
		num_of_pats++;

		npat_len = GetNextNum(fp);
	}
	fclose(fp);

	return num_of_pats;
}

int PAT_MAP::LoadNegBdPats(char* sznegbd_filename, PATTERN* &ppatterns, ITEM* &ppat_buf)
{
	FILE *fp;
	int npat_len, nitem, npat_sup, num_of_pats, nbuf_size, nbuf_pos, i;

	fp = fopen(sznegbd_filename, "rt");
	if(fp==NULL)
	{
		printf("Error: cannot open file %s for read\n", sznegbd_filename);
		return 0;
	}

	num_of_pats = 0;
	nbuf_size = 0;

	npat_len = GetNextNum(fp);
	while(!feof(fp))
	{
		for(i=0;i<npat_len;i++)
			nitem = GetNextNum(fp);
		npat_sup = GetNextNum(fp);
		num_of_pats++;
		nbuf_size += npat_len;

		npat_len = GetNextNum(fp);
	}
	rewind(fp);
	if(num_of_pats==0)
	{
		fclose(fp);
		return 0;
	}

	ppatterns = new PATTERN[num_of_pats];
	ppat_buf = new ITEM[nbuf_size];
	nbuf_pos = 0;
	num_of_pats = 0;

	npat_len = GetNextNum(fp);
	while(!feof(fp))
	{
		ppatterns[num_of_pats].nlen = npat_len;
		ppatterns[num_of_pats].pitemset = &(ppat_buf[nbuf_pos]);
		nbuf_pos += npat_len;
		for(i=0;i<npat_len;i++)
			ppatterns[num_of_pats].pitemset[i] = GetNextNum(fp);
		ppatterns[num_of_pats].nsup = GetNextNum(fp);
		num_of_pats++;

		npat_len = GetNextNum(fp);
	}
	fclose(fp);

	return num_of_pats;
}


unsigned int PAT_MAP::HashFunc(unsigned int nmap_value)
{
	return nmap_value%mnpat_map_size;
}


void PAT_MAP::InsertOnePat(PATTERN *ppat)
{
	PAT_MAP_NODE *pmap_node;
	unsigned int nmap_value;

	pmap_node = &(mpmap_node_buf[mnmap_buf_pos]);
	mnmap_buf_pos++;

	pmap_node->ppattern = ppat;

	nmap_value = HashItemset(ppat->pitemset, ppat->nlen);
	ppat->nmap_value = nmap_value;

	nmap_value = HashFunc(nmap_value);

	pmap_node->pnext = mppat_map[nmap_value];
	mppat_map[nmap_value] = pmap_node;

}


void PAT_MAP::BuildPatHashMap(char* szpat_filename, int npat_type)
{
	int i;
	if(npat_type==0)
		mnum_of_pats = LoadFG(szpat_filename, mppatterns, mppat_buf);
	else if(npat_type==1)
		mnum_of_pats = LoadFreqBdPats(szpat_filename, mppatterns, mppat_buf);
	else if(npat_type==2)
		mnum_of_pats = LoadNegBdPats(szpat_filename, mppatterns, mppat_buf);

	mnpat_map_size = mnum_of_pats;

	if(mnum_of_pats>0)
	{
		mpmap_node_buf = new PAT_MAP_NODE[mnum_of_pats];
		mppat_map = new PAT_MAP_NODE*[mnpat_map_size];
		memset(mppat_map, 0, sizeof(PAT_MAP_NODE*)*mnpat_map_size);
		mnmap_buf_pos = 0;

		for(i=0;i<mnum_of_pats;i++)
		{
			if(!(mppatterns[i].nlen==1 && mppatterns[i].pitemset[0]>=gnmax_item_id))
				InsertOnePat(&(mppatterns[i]));
		}
	}

	mnsearch_times = 0;
	mdavg_search_depth = 0;

}

void PAT_MAP::DelPatMap()
{
	if(mnum_of_pats>0)
	{
		delete []mpmap_node_buf;
		delete []mppat_map;

		delete []mppatterns;
		delete []mppat_buf;
	}

	if(mnsearch_times>0)
		mdavg_search_depth /= mnsearch_times;
	else
		mdavg_search_depth = 0;

	//printf("Frequent generators: %d, average search depth: %f\n", mnsearch_times, mdavg_search_depth);

}

int PAT_MAP::SearchPat(int npat_len)
{
	PAT_MAP_NODE* pmap_node;
	PATTERN* ppat;
	int i;
	unsigned int nmap_value;

	nmap_value = HashFunc(gnmap_value);

	if(mppat_map[nmap_value]==NULL)
		return -1;
	else 
	{
		//mnsearch_times++;
		pmap_node = mppat_map[nmap_value];
		while(pmap_node!=NULL)
		{
			//mdavg_search_depth++;
			ppat = pmap_node->ppattern;
			if(ppat->nlen==npat_len && ppat->nmap_value==gnmap_value)
			{
				for(i=0;i<ppat->nlen;i++)
				{
					if(gpitem_bitmap[ppat->pitemset[i]]==-1)
						break;
				}
				if(i==ppat->nlen)
				{
					gnrdnt_item_pos = gpitem_bitmap[ppat->pitemset[0]];
					return ppat->nsup;
				}
			}
			pmap_node = pmap_node->pnext;
		}
	}
	return -1;
}



