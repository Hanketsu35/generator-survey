#include <string.h>

#include "parameters.h"
#include "Global.h"

CParameters goparameters;


void CParameters::SetResultName(char *szresult_name)
{
	sprintf(szgenerator_filename, "%s.txt", szresult_name);
	sprintf(sznegborder_filename, "%s.fbd", szresult_name);
}

