#pragma once 

#include "Global.h"


#define DEFAULT_TREE_OUTBUF_SIZE		(1<<29)
#define DEFAULT_TREE_BUF_PAGE_SIZE		18


class CParameters
{
public:
	char szdata_filename[MAX_FILENAME_LEN];
	int nmin_sup;
	int k;
	bool bresult_name_given;
	char szgenerator_filename[MAX_FILENAME_LEN];
	char sznegborder_filename[MAX_FILENAME_LEN];
	char szcoveritem_filename[MAX_FILENAME_LEN];

	int nfpnode_buf_size;

	int ntree_outbuf_size;
	int ntree_buf_page_size;
	int ntree_buf_num_of_pages;

	void SetResultName(char *szresult_name);
	void SetBufParameters();

	void SetIncoreParameters();
	void SetOutofcoreParameters();

};

extern CParameters goparameters;

