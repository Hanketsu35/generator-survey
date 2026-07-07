#include <string.h>

#include "parameters.h"
#include "Global.h"

CParameters goparameters;


void CParameters::SetResultName(char *szresult_name)
{
	sprintf(szgenerator_filename, "%s.txt", szresult_name);
	sprintf(sznegborder_filename, "%s.nbd", szresult_name);
	sprintf(szcoveritem_filename, "%s.cov", szresult_name);

}

